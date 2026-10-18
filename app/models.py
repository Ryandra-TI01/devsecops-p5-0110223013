"""SQLAlchemy ORM models for the Expense Tracker API."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Integer, String, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TWO_PLACES = Decimal("0.01")


class TransactionType(StrEnum):
    """Allowed transaction types."""

    INCOME = "income"
    EXPENSE = "expense"


class SqliteDecimal(TypeDecorator[Decimal]):
    """Store Decimal values as minor units (integer cents) in SQLite for exact precision.

    Avoids SQLite floating-point coercion while preserving exact two-decimal-place
    representation for monetary values.
    """

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Decimal | int | str | None, dialect: object) -> int | None:
        """Convert a Python Decimal amount into integer minor units (cents)."""
        if value is None:
            return None
        quantized = Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        return int(quantized * 100)

    def process_result_value(self, value: int | None, dialect: object) -> Decimal | None:
        """Convert integer minor units (cents) back into a two-decimal-place Decimal."""
        if value is None:
            return None
        return (Decimal(value) / Decimal(100)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class Transaction(Base):
    """ORM model representing an income or expense transaction."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_transactions_valid_type",
        ),
        CheckConstraint("length(trim(category)) > 0", name="ck_transactions_category_non_empty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    amount: Mapped[Decimal] = mapped_column(
        "amount_cents",
        SqliteDecimal(),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

