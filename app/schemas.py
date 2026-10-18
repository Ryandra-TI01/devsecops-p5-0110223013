"""Pydantic request and response schemas for the Expense Tracker API."""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models import TWO_PLACES, TransactionType

MAX_AMOUNT = Decimal("9999999999.99")


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    amount: Decimal = Field(
        ...,
        description="Positive monetary amount with at most 2 decimal places.",
        examples=["125.50"],
    )
    type: TransactionType = Field(
        ...,
        description="Transaction type: 'income' or 'expense'.",
        examples=[TransactionType.EXPENSE],
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Non-empty category label (e.g., 'groceries', 'salary').",
        examples=["groceries"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional transaction description.",
        examples=["Weekly supermarket purchase"],
    )

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount_input(cls, value: Any) -> Decimal:
        """Convert input to Decimal without floating-point precision loss and validate bounds."""
        if isinstance(value, bool):
            raise ValueError("Amount must be a valid decimal number, not a boolean.")
        if isinstance(value, float):
            # Convert via string representation to avoid binary float artifacts
            value = str(value)
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError("Amount must be a valid decimal number.") from exc

        if not decimal_value.is_finite():
            raise ValueError("Amount must be a finite decimal number.")

        if decimal_value <= Decimal("0"):
            raise ValueError("Amount must be greater than zero.")

        exponent = decimal_value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places.")

        if decimal_value > MAX_AMOUNT:
            raise ValueError(f"Amount cannot exceed {MAX_AMOUNT}.")

        return decimal_value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        """Ensure category is non-empty after stripping whitespace."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Category must not be empty or whitespace only.")
        return cleaned


class TransactionResponse(BaseModel):
    """Schema representing a stored transaction."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    type: TransactionType
    category: str
    description: str | None = None
    created_at: datetime

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> Decimal:
        """Ensure amount is quantized to 2 decimal places."""
        return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class SummaryResponse(BaseModel):
    """Schema representing aggregated income, expense, and net balance totals."""

    total_income: Decimal = Field(
        ...,
        description="Sum of all income transactions.",
    )
    total_expenses: Decimal = Field(
        ...,
        description="Sum of all expense transactions.",
    )
    net_balance: Decimal = Field(
        ...,
        description="Net balance calculated as total_income - total_expenses.",
    )
    transaction_count: int = Field(
        default=0,
        description="Total number of transactions included in the summary.",
    )


class HealthResponse(BaseModel):
    """Schema for the health-check endpoint."""

    status: str = Field(default="ok", examples=["ok"])
    service: str = Field(default="expense-tracker-api", examples=["expense-tracker-api"])


class ErrorDetail(BaseModel):
    """Structured error response body."""

    error: str = Field(..., description="Short error code or category.")
    message: str = Field(..., description="Human-readable error description.")
    details: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional validation error details.",
    )

