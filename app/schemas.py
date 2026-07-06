from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


SCHOLAR_NUMBER_REGEX = r"^[A-Za-z0-9_-]{4,20}$"


class SignupRequest(BaseModel):
    scholar_number: str = Field(pattern=SCHOLAR_NUMBER_REGEX)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("scholar_number")
    @classmethod
    def normalize_trimmed(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    scholar_number: str = Field(pattern=SCHOLAR_NUMBER_REGEX)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("scholar_number")
    @classmethod
    def normalize_trimmed(cls, value: str) -> str:
        return value.strip()


class UserOut(BaseModel):
    scholar_number: str
    full_name: str
    hostel_number: str
    room_number: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SubmissionUpsertRequest(BaseModel):
    wants_change: bool
    wanted_roommate_name: str | None = Field(default=None, min_length=2, max_length=120)
    wanted_roommate_scholar_number: str | None = Field(default=None, pattern=SCHOLAR_NUMBER_REGEX)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("wanted_roommate_name", "wanted_roommate_scholar_number", "notes")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    @model_validator(mode="after")
    def validate_roommate_fields(self):
        if self.wants_change and (not self.wanted_roommate_name or not self.wanted_roommate_scholar_number):
            raise ValueError("Roommate name and scholar number are required when wants_change=true")
        return self


class SubmissionOut(BaseModel):
    id: int
    student_scholar_number: str
    student_name: str
    student_hostel_number: str
    student_room_number: str
    wants_change: bool
    wanted_roommate_name: str | None
    wanted_roommate_scholar_number: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ActiveCycleOut(BaseModel):
    id: int
    name: str
    is_active: bool
    starts_at: datetime
    ends_at: datetime | None


class AllocationOut(BaseModel):
    id: int
    hostel_number: str
    room_number: str
    student_one_scholar_number: str
    student_one_name: str
    student_two_scholar_number: str
    student_two_name: str
    created_at: datetime


class PairOut(BaseModel):
    student_one_scholar_number: str
    student_one_name: str
    student_two_scholar_number: str
    student_two_name: str


class RoomOut(BaseModel):
    hostel_number: str
    room_number: str


class AllocationRunResponse(BaseModel):
    empty_rooms_detected: list[RoomOut]
    mutual_pairs_found: list[PairOut]
    unallocated_pairs: list[PairOut]
    allocations: list[AllocationOut]
