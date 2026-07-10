import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import engine, SessionLocal
from app.models import Base, Student

SCHOLAR_RE = re.compile(r"^\d{8,15}$")
ROOM_RE = re.compile(r"^\d{3,6}$")
HOSTEL_IN_LINE_RE = re.compile(r"^H-\d+\s*[A-Za-z]?$", re.IGNORECASE)


def normalize_spaces(value: str) -> str:
    return " ".join(value.strip().split())


def parse_hostel_heading(line: str) -> str | None:
    match = re.search(r"Hostel\s*No\s*-\s*([0-9]+)\s*\(?([A-Za-z])?\)?", line, flags=re.IGNORECASE)
    if not match:
        return None
    block = match.group(1)
    wing = (match.group(2) or "").upper()
    return f"H-{block}{(' ' + wing) if wing else ''}".strip()


def parse_records(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    records: list[dict[str, str]] = []
    
    # Try horizontal single-line parser first
    single_line_pattern = re.compile(
        r"^\s*(\d+)\s+(.+?)\s+(\d{8,15})\s+(\S+)(?:\s+(?:Double|Single|Occupancy))?", 
        re.IGNORECASE
    )
    
    for line in lines:
        match = single_line_pattern.match(line)
        if match:
            name = normalize_spaces(match.group(2))
            scholar_number = match.group(3)
            code = match.group(4)
            
            code_match = re.match(r"^[Hh](\d+)-?([A-Za-z]+)(\d+)", code)
            if code_match:
                hostel_num = int(code_match.group(1))
                wing = code_match.group(2).upper()
                room_num = code_match.group(3)
                
                hostel_number = f"H-{hostel_num:02d} {wing}"
                room_number = f"{hostel_num}{room_num}"
            else:
                hostel_number = "UNKNOWN"
                room_number = code
                
            records.append(
                {
                    "scholar_number": scholar_number,
                    "full_name": name,
                    "hostel_number": hostel_number,
                    "room_number": room_number,
                }
            )
            
    if records:
        return records

    # Fallback to original vertical parser
    current_hostel = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        hostel_from_heading = parse_hostel_heading(line)
        if hostel_from_heading:
            current_hostel = hostel_from_heading
            i += 1
            continue

        if not line.isdigit():
            i += 1
            continue

        i += 1
        name_parts: list[str] = []
        while i < len(lines) and not SCHOLAR_RE.match(lines[i]):
            candidate = lines[i]
            if candidate.lower() in {"double", "single", "occupancy", "s.no.", "hostel", "number", "room", "no."}:
                i += 1
                continue
            name_parts.append(candidate)
            i += 1

        if i >= len(lines) or not SCHOLAR_RE.match(lines[i]):
            continue

        scholar_number = lines[i]
        i += 1

        hostel_number = current_hostel
        if i < len(lines) and HOSTEL_IN_LINE_RE.match(lines[i]):
            hostel_number = normalize_spaces(lines[i].upper())
            i += 1

        if i >= len(lines) or not ROOM_RE.match(lines[i]):
            continue
        room_number = lines[i]
        i += 1

        if i < len(lines) and lines[i].lower().startswith("double"):
            i += 1

        full_name = normalize_spaces(" ".join(name_parts))
        if not full_name:
            continue

        records.append(
            {
                "scholar_number": scholar_number,
                "full_name": full_name,
                "hostel_number": hostel_number or "UNKNOWN",
                "room_number": room_number,
            }
        )
    return records



def main():
    parser = argparse.ArgumentParser(description="Import hostel students from pasted feed into database.")
    parser.add_argument("--file", required=True, help="Path to the pasted hostel data text file")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Drop and recreate all application tables before import",
    )
    args = parser.parse_args()

    source_file = Path(args.file)
    if not source_file.exists():
        raise FileNotFoundError(f"Input file not found: {source_file}")

    if args.reset_db:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    records = parse_records(source_file.read_text(encoding="utf-8"))
    if not records:
        raise ValueError("No student records parsed from input file")

    db = SessionLocal()
    try:
        for row in records:
            student = db.query(Student).filter(Student.scholar_number == row["scholar_number"]).first()
            if student:
                student.full_name = row["full_name"]
                student.hostel_number = row["hostel_number"]
                student.room_number = row["room_number"]
            else:
                db.add(
                    Student(
                        scholar_number=row["scholar_number"],
                        full_name=row["full_name"],
                        hostel_number=row["hostel_number"],
                        room_number=row["room_number"],
                        password_hash=None,
                    )
                )
        db.commit()
    finally:
        db.close()

    print(f"Imported/updated {len(records)} student records from {source_file}")


if __name__ == "__main__":
    main()
