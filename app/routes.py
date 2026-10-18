"""API route definitions for the Expense Tracker application."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import TransactionType
from app.schemas import (
    ErrorDetail,
    HealthResponse,
    SummaryResponse,
    TransactionCreate,
    TransactionResponse,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check endpoint",
)
def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok", service="expense-tracker-api")


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Transactions"],
    summary="Create a new income or expense transaction",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorDetail,
            "description": "Validation error in request payload.",
        }
    },
)
def create_transaction_endpoint(
    payload: TransactionCreate,
    db: DbSession,
) -> TransactionResponse:
    """Create and persist a new transaction."""
    transaction = services.create_transaction(db=db, payload=payload)
    return TransactionResponse.model_validate(transaction)


@router.get(
    "/transactions/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Summary"],
    summary="Calculate financial summary (income, expenses, net balance)",
)
def get_transactions_summary_endpoint(db: DbSession) -> SummaryResponse:
    """Return aggregated total income, total expenses, and net balance."""
    return services.calculate_summary(db=db)


@router.get(
    "/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Summary"],
    summary="Calculate financial summary (income, expenses, net balance)",
)
def get_summary_endpoint(db: DbSession) -> SummaryResponse:
    """Return aggregated total income, total expenses, and net balance."""
    return services.calculate_summary(db=db)


@router.get(
    "/transactions",
    response_model=list[TransactionResponse],
    status_code=status.HTTP_200_OK,
    tags=["Transactions"],
    summary="List transactions with optional type and category filters",
)
def list_transactions_endpoint(
    db: DbSession,
    transaction_type: Annotated[
        TransactionType | None,
        Query(
            alias="type",
            description="Filter transactions by type ('income' or 'expense').",
        ),
    ] = None,
    category: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Filter transactions by category name (case-insensitive).",
        ),
    ] = None,
) -> list[TransactionResponse]:
    """List stored transactions, optionally filtering by transaction type and category."""
    transactions = services.list_transactions(
        db=db,
        transaction_type=transaction_type,
        category=category,
    )
    return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Transactions"],
    summary="Retrieve a transaction by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Transaction not found.",
        }
    },
)
def get_transaction_endpoint(
    db: DbSession,
    transaction_id: Annotated[
        int,
        Path(gt=0, description="Positive integer ID of the transaction."),
    ],
) -> TransactionResponse:
    """Retrieve a single transaction by its unique ID."""
    transaction = services.get_transaction_by_id(db=db, transaction_id=transaction_id)
    return TransactionResponse.model_validate(transaction)


@router.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Transactions"],
    summary="Delete a transaction by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Transaction not found.",
        }
    },
)
def delete_transaction_endpoint(
    db: DbSession,
    transaction_id: Annotated[
        int,
        Path(gt=0, description="Positive integer ID of the transaction to delete."),
    ],
) -> Response:
    """Delete an existing transaction by its unique ID."""
    services.delete_transaction(db=db, transaction_id=transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

