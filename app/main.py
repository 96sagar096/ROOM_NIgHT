import csv
import io
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Base, ExchangeCycle, Student, VoteSubmission
from app.schemas import (
    ActiveCycleOut,
    AuthResponse,
    LoginRequest,
    SignupRequest,
    SubmissionOut,
    SubmissionUpsertRequest,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password
from app.deps import get_current_admin, get_current_user
from app.database import engine

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)


def get_or_create_active_cycle(db: Session) -> ExchangeCycle:
    cycle = db.query(ExchangeCycle).filter(ExchangeCycle.is_active.is_(True)).first()
    if cycle:
        return cycle

    cycle = ExchangeCycle(name="default-active-cycle", is_active=True)
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


def serialize_submission(submission: VoteSubmission) -> SubmissionOut:
    return SubmissionOut(
        id=submission.id,
        student_scholar_number=submission.student.scholar_number,
        student_name=submission.student.full_name,
        student_hostel_number=submission.student.hostel_number,
        student_room_number=submission.student.room_number,
        wants_change=submission.wants_change,
        wanted_roommate_name=submission.wanted_roommate_name,
        wanted_roommate_scholar_number=submission.wanted_roommate_scholar_number,
        notes=submission.notes,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


def build_submissions_query(
    db: Session,
    cycle_id: int,
    scholar_number: str | None = None,
    wants_change: bool | None = None,
):
    query = db.query(VoteSubmission).join(Student).filter(VoteSubmission.cycle_id == cycle_id)

    conditions = []
    if scholar_number:
        conditions.append(Student.scholar_number.ilike(f"%{scholar_number.strip()}%"))
    if wants_change is not None:
        conditions.append(VoteSubmission.wants_change.is_(wants_change))
    if conditions:
        query = query.filter(and_(*conditions))
    return query.order_by(VoteSubmission.updated_at.desc())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    user = db.query(Student).filter(Student.scholar_number == payload.scholar_number).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholar number not found in hostel data")
    if user.password_hash:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already initialized, please login")

    user.password_hash = hash_password(payload.password)
    if payload.scholar_number in settings.admin_scholar_number_set:
        user.is_admin = True
    db.commit()
    db.refresh(user)

    token = create_access_token(user.scholar_number)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Student).filter(Student.scholar_number == payload.scholar_number).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scholar number or password")

    token = create_access_token(user.scholar_number)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@app.get("/api/me", response_model=UserOut)
def get_me(current_user: Student = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@app.get("/api/cycles/active", response_model=ActiveCycleOut)
def get_active_cycle(db: Session = Depends(get_db), _: Student = Depends(get_current_user)):
    cycle = get_or_create_active_cycle(db)
    return ActiveCycleOut(
        id=cycle.id,
        name=cycle.name,
        is_active=cycle.is_active,
        starts_at=cycle.starts_at,
        ends_at=cycle.ends_at,
    )


@app.get("/api/submission", response_model=SubmissionOut | None)
def get_my_submission(db: Session = Depends(get_db), current_user: Student = Depends(get_current_user)):
    cycle = get_or_create_active_cycle(db)
    submission = (
        db.query(VoteSubmission)
        .filter(VoteSubmission.student_id == current_user.id, VoteSubmission.cycle_id == cycle.id)
        .first()
    )
    if not submission:
        return None
    return serialize_submission(submission)


@app.put("/api/submission", response_model=SubmissionOut)
def upsert_submission(
    payload: SubmissionUpsertRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    cycle = get_or_create_active_cycle(db)
    wanted_scholar = payload.wanted_roommate_scholar_number
    if payload.wants_change and wanted_scholar == current_user.scholar_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wanted roommate scholar number cannot be your own scholar number",
        )

    if payload.wants_change and wanted_scholar:
        wanted_user = db.query(Student).filter(Student.scholar_number == wanted_scholar).first()
        if not wanted_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wanted roommate not found")

    submission = (
        db.query(VoteSubmission)
        .filter(VoteSubmission.student_id == current_user.id, VoteSubmission.cycle_id == cycle.id)
        .first()
    )
    if not submission:
        submission = VoteSubmission(student_id=current_user.id, cycle_id=cycle.id, wants_change=False)
        db.add(submission)

    submission.wants_change = payload.wants_change
    submission.wanted_roommate_name = payload.wanted_roommate_name if payload.wants_change else None
    submission.wanted_roommate_scholar_number = wanted_scholar if payload.wants_change else None
    submission.notes = payload.notes

    db.commit()
    db.refresh(submission)
    db.refresh(current_user)
    return serialize_submission(submission)


@app.get("/api/submissions", response_model=list[SubmissionOut])
def list_submissions(
    scholar_number: str | None = Query(default=None),
    wants_change: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Student = Depends(get_current_user),
):
    cycle = get_or_create_active_cycle(db)
    submissions = build_submissions_query(db, cycle.id, scholar_number, wants_change).all()
    return [serialize_submission(item) for item in submissions]


@app.get("/api/admin/submissions", response_model=list[SubmissionOut])
def admin_list_submissions(
    scholar_number: str | None = Query(default=None),
    wants_change: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Student = Depends(get_current_admin),
):
    cycle = get_or_create_active_cycle(db)
    submissions = build_submissions_query(db, cycle.id, scholar_number, wants_change).all()
    return [serialize_submission(item) for item in submissions]


@app.get("/api/admin/submissions/export.csv")
def export_submissions_csv(
    db: Session = Depends(get_db),
    _: Student = Depends(get_current_admin),
):
    cycle = get_or_create_active_cycle(db)
    submissions = build_submissions_query(db, cycle.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "student_scholar_number",
            "student_name",
            "student_hostel_number",
            "student_room_number",
            "wants_change",
            "wanted_roommate_name",
            "wanted_roommate_scholar_number",
            "notes",
            "updated_at",
        ]
    )
    for row in submissions:
        writer.writerow(
            [
                row.student.scholar_number,
                row.student.full_name,
                row.student.hostel_number,
                row.student.room_number,
                row.wants_change,
                row.wanted_roommate_name or "",
                row.wanted_roommate_scholar_number or "",
                row.notes or "",
                row.updated_at.isoformat(),
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=submissions.csv"},
    )
