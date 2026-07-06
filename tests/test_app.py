from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base, Student

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_hostel_exchange.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                Student(scholar_number="25112011235", full_name="Sagar Burra", hostel_number="H-10 A", room_number="10003"),
                Student(scholar_number="25116011224", full_name="Harsh Raj", hostel_number="H-10 A", room_number="10003"),
                Student(scholar_number="25112011112", full_name="Jay Agrawal", hostel_number="H-08 B", room_number="8127"),
            ]
        )
        db.commit()
    finally:
        db.close()


def signup_user(scholar_number: str, password: str = "password123"):
    return client.post(
        "/api/auth/signup",
        json={
            "scholar_number": scholar_number,
            "password": password,
        },
    )


def login_user(scholar_number: str, password: str = "password123"):
    return client.post("/api/auth/login", json={"scholar_number": scholar_number, "password": password})


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_signup_and_login_for_preloaded_student():
    resp = signup_user("25112011235")
    assert resp.status_code == 200
    assert resp.json()["user"]["full_name"] == "Sagar Burra"

    login_resp = login_user("25112011235")
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["hostel_number"] == "H-10 A"


def test_signup_rejects_unknown_scholar_number():
    resp = signup_user("99999999999")
    assert resp.status_code == 404


def test_submission_flow_and_visibility():
    first = signup_user("25112011235")
    second = signup_user("25112011112")
    t1 = first.json()["access_token"]

    update = client.put(
        "/api/submission",
        headers=auth_headers(t1),
        json={
            "wants_change": True,
            "wanted_roommate_name": "Jay Agrawal",
            "wanted_roommate_scholar_number": "25112011112",
            "notes": "Want same study schedule",
        },
    )
    assert update.status_code == 200
    assert update.json()["wanted_roommate_scholar_number"] == "25112011112"

    list_resp = client.get("/api/submissions", headers=auth_headers(second.json()["access_token"]))
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["student_scholar_number"] == "25112011235"
    assert data[0]["student_hostel_number"] == "H-10 A"


def test_self_reference_roommate_not_allowed():
    first = signup_user("25112011235")
    token = first.json()["access_token"]
    update = client.put(
        "/api/submission",
        headers=auth_headers(token),
        json={
            "wants_change": True,
            "wanted_roommate_name": "Me",
            "wanted_roommate_scholar_number": "25112011235",
        },
    )
    assert update.status_code == 400
