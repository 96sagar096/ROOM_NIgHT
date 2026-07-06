# Hostel Room Exchange (Double Occupancy)

A deployment-ready FastAPI web app where hostel students can:
- Create first-time password (signup) and then login with scholar number + password
- Submit whether they want a room change
- Request a preferred roommate by name + scholar number
- View individual submissions from other students
- Allow admins to run room allocation based on mutual pairing + empty-room rule

Students are imported from hostel feed data (room + hostel already mapped) and signup is only allowed for preloaded scholar numbers.

## Tech stack
- FastAPI + SQLAlchemy + SQLite (configurable via `DATABASE_URL`)
- JWT auth
- Server-rendered static frontend (HTML/CSS/JS)
- Docker support

## Quick start (local)
1. Create env file:
   ```bash
   cp .env.example .env
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open:
   - UI: `http://localhost:8000/`
   - Health: `http://localhost:8000/health`
   - API docs: `http://localhost:8000/docs`

## Import student feed into database
Use the provided parser/importer:
```bash
python scripts/import_students.py --file /path/to/pasted-students.txt --reset-db
```

This loads/updates student records with scholar number, name, hostel number, and room number. Imported students can then complete first-time signup by creating their password.

## Allocation rule implemented
1. If both current occupants of a double-occupancy room submit `wants_change=true`, that room is marked as an empty room candidate.
2. Students are paired only when roommate preference is mutual (A requests B and B requests A).
3. Mutual pairs are allocated to detected empty rooms in sorted order.
4. Admin can run allocation from UI button or API:
   - `POST /api/admin/allocations/run`
   - `GET /api/admin/allocations`

## Docker deployment
```bash
cp .env.example .env
docker compose up --build
```

## Admin access
Users are marked admin automatically when their scholar number is listed in:
```
ADMIN_SCHOLAR_NUMBERS=ADMIN001,ADMIN002
```

## Tests
```bash
pytest -q
```
