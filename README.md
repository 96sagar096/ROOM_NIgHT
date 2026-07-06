# Hostel Room Exchange (Double Occupancy)

A deployment-ready FastAPI web app where hostel students can:
- Create first-time password (signup) and then login with scholar number + password
- Submit whether they want a room change
- Request a preferred roommate by name + scholar number
- View individual submissions from other students

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
