"""Business logic and data access operations for transactions."""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import TWO_PLACES, Transaction, TransactionType
from app.schemas import SummaryResponse, TransactionCreate


class TransactionNotFoundError(Exception):
    """Raised when a requested transaction ID does not exist."""

    def __init__(self, transaction_id: int) -> None:
        self.transaction_id = transaction_id
        super().__init__(f"Transaction with ID {transaction_id} was not found.")


def create_transaction(db: Session, payload: TransactionCreate) -> Transaction:
    """Persist a new income or expense transaction in the database."""
    quantized_amount = payload.amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    transaction = Transaction(
        amount=quantized_amount,
        type=payload.type.value,
        category=payload.category,
        description=payload.description,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transaction_by_id(db: Session, transaction_id: int) -> Transaction:
    """Retrieve a single transaction by its primary key or raise TransactionNotFoundError."""
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    transaction = db.scalar(stmt)
    if transaction is None:
        raise TransactionNotFoundError(transaction_id)
    return transaction


def list_transactions(
    db: Session,
    transaction_type: TransactionType | None = None,
    category: str | None = None,
) -> list[Transaction]:
    """List transactions ordered by ID ascending, optionally filtered by type and category."""
    stmt = select(Transaction)

    if transaction_type is not None:
        stmt = stmt.where(Transaction.type == transaction_type.value)

    if category is not None:
        cleaned_category = category.strip()
        if cleaned_category:
            stmt = stmt.where(func.lower(Transaction.category) == cleaned_category.lower())

    stmt = stmt.order_by(Transaction.id.asc())
    return list(db.scalars(stmt).all())


def delete_transaction(db: Session, transaction_id: int) -> None:
    """Delete a transaction by ID or raise TransactionNotFoundError if missing."""
    transaction = get_transaction_by_id(db, transaction_id)
    db.delete(transaction)
    db.commit()


def calculate_summary(db: Session) -> SummaryResponse:
    """Calculate total income, total expenses, and net balance using exact Decimal arithmetic."""
    stmt = select(Transaction)
    transactions = list(db.scalars(stmt).all())

    total_income = Decimal("0.00")
    total_expenses = Decimal("0.00")

    for tx in transactions:
        amount = Decimal(str(tx.amount)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if tx.type == TransactionType.INCOME.value:
            total_income += amount
        elif tx.type == TransactionType.EXPENSE.value:
            total_expenses += amount

    total_income = total_income.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total_expenses = total_expenses.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    net_balance = (total_income - total_expenses).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    return SummaryResponse(
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        transaction_count=len(transactions),
    )

