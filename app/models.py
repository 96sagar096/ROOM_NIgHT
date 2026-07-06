from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    scholar_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hostel_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    room_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    submissions: Mapped[list["VoteSubmission"]] = relationship(back_populates="student")


class ExchangeCycle(Base):
    __tablename__ = "exchange_cycles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    submissions: Mapped[list["VoteSubmission"]] = relationship(back_populates="cycle")


class VoteSubmission(Base):
    __tablename__ = "vote_submissions"
    __table_args__ = (UniqueConstraint("student_id", "cycle_id", name="uq_student_cycle_submission"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("exchange_cycles.id"), nullable=False, index=True)
    wants_change: Mapped[bool] = mapped_column(Boolean, nullable=False)
    wanted_roommate_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    wanted_roommate_scholar_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    student: Mapped["Student"] = relationship(back_populates="submissions")
    cycle: Mapped["ExchangeCycle"] = relationship(back_populates="submissions")
