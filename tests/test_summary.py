"""Tests for financial summary calculation and exact Decimal precision."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TransactionType
from app.schemas import TransactionCreate
from app.services import calculate_summary, create_transaction


def test_summary_empty_database(client: TestClient) -> None:
    """Verify summary returns zeros when no transactions exist."""
    response = client.get("/transactions/summary")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["total_income"])) == Decimal("0.00")
    assert Decimal(str(data["total_expenses"])) == Decimal("0.00")
    assert Decimal(str(data["net_balance"])) == Decimal("0.00")
    assert data["transaction_count"] == 0

    # Also verify alias endpoint /summary
    alias_response = client.get("/summary")
    assert alias_response.status_code == 200
    assert alias_response.json() == data


def test_summary_only_income(client: TestClient) -> None:
    """Verify summary when only income transactions exist."""
    client.post("/transactions", json={"amount": "1500.00", "type": "income", "category": "salary"})
    client.post("/transactions", json={"amount": "250.50", "type": "income", "category": "dividends"})

    response = client.get("/transactions/summary")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["total_income"])) == Decimal("1750.50")
    assert Decimal(str(data["total_expenses"])) == Decimal("0.00")
    assert Decimal(str(data["net_balance"])) == Decimal("1750.50")
    assert data["transaction_count"] == 2


def test_summary_only_expenses_negative_balance(client: TestClient) -> None:
    """Verify summary when only expenses exist results in negative net balance."""
    client.post("/transactions", json={"amount": "400.00", "type": "expense", "category": "rent"})
    client.post("/transactions", json={"amount": "150.75", "type": "expense", "category": "utilities"})

    response = client.get("/transactions/summary")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["total_income"])) == Decimal("0.00")
    assert Decimal(str(data["total_expenses"])) == Decimal("550.75")
    assert Decimal(str(data["net_balance"])) == Decimal("-550.75")
    assert data["transaction_count"] == 2


def test_summary_mixed_transactions_and_decimal_precision(client: TestClient) -> None:
    """Verify exact financial calculations avoid binary floating point drift."""
    # Classical float drift values: 0.10 + 0.20 != 0.30 in IEEE 754 floats
    client.post("/transactions", json={"amount": "0.10", "type": "income", "category": "interest"})
    client.post("/transactions", json={"amount": "0.20", "type": "income", "category": "cashback"})
    client.post("/transactions", json={"amount": "0.15", "type": "expense", "category": "fee"})

    response = client.get("/transactions/summary")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["total_income"])) == Decimal("0.30")
    assert Decimal(str(data["total_expenses"])) == Decimal("0.15")
    assert Decimal(str(data["net_balance"])) == Decimal("0.15")
    assert data["transaction_count"] == 3


def test_summary_service_unit_test(db_session: Session) -> None:
    """Directly test calculate_summary service function with large numbers."""
    create_transaction(
        db_session,
        TransactionCreate(amount=Decimal("9999999.99"), type=TransactionType.INCOME, category="investment"),
    )
    create_transaction(
        db_session,
        TransactionCreate(amount=Decimal("1234567.89"), type=TransactionType.EXPENSE, category="property"),
    )

    summary = calculate_summary(db_session)
    assert summary.total_income == Decimal("9999999.99")
    assert summary.total_expenses == Decimal("1234567.89")
    assert summary.net_balance == Decimal("8765432.10")
    assert summary.transaction_count == 2

