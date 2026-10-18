"""Unit and API tests for the Expense Tracker API."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import TransactionType
from app.schemas import TransactionCreate
from app.services import calculate_summary, create_transaction


def test_health_check(client: TestClient) -> None:
    """Verify the health-check endpoint returns HTTP 200 and expected status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "expense-tracker-api"}


def test_create_and_retrieve_transaction(client: TestClient) -> None:
    """Verify creating an expense transaction and retrieving it by ID."""
    payload = {
        "amount": "45.75",
        "type": "expense",
        "category": "groceries",
        "description": "Weekly produce",
    }
    create_resp = client.post("/transactions", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["id"] == 1
    assert Decimal(str(created["amount"])) == Decimal("45.75")
    assert created["type"] == "expense"
    assert created["category"] == "groceries"
    assert created["description"] == "Weekly produce"
    assert "created_at" in created

    get_resp = client.get(f"/transactions/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json() == created


def test_list_and_filter_transactions(client: TestClient) -> None:
    """Verify listing transactions and filtering by type and category."""
    samples = [
        {"amount": "2500.00", "type": "income", "category": "salary", "description": "Monthly pay"},
        {"amount": "120.50", "type": "expense", "category": "groceries", "description": "Market"},
        {"amount": "60.00", "type": "expense", "category": "utilities", "description": "Internet"},
    ]
    for sample in samples:
        resp = client.post("/transactions", json=sample)
        assert resp.status_code == 201

    all_resp = client.get("/transactions")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 3

    expense_resp = client.get("/transactions", params={"type": "expense"})
    assert expense_resp.status_code == 200
    expenses = expense_resp.json()
    assert len(expenses) == 2
    assert all(tx["type"] == "expense" for tx in expenses)

    category_resp = client.get("/transactions", params={"category": "GROCERIES"})
    assert category_resp.status_code == 200
    groceries = category_resp.json()
    assert len(groceries) == 1
    assert groceries[0]["category"] == "groceries"

    combined_resp = client.get("/transactions", params={"type": "income", "category": "salary"})
    assert combined_resp.status_code == 200
    assert len(combined_resp.json()) == 1


def test_delete_transaction_and_missing_record(client: TestClient) -> None:
    """Verify deleting a transaction by ID and handling 404 for non-existent IDs."""
    create_resp = client.post(
        "/transactions",
        json={"amount": "15.00", "type": "expense", "category": "transport"},
    )
    tx_id = create_resp.json()["id"]

    del_resp = client.delete(f"/transactions/{tx_id}")
    assert del_resp.status_code == 204

    get_missing = client.get(f"/transactions/{tx_id}")
    assert get_missing.status_code == 404
    error_body = get_missing.json()
    assert error_body["error"] == "not_found"
    assert str(tx_id) in error_body["message"]

    del_missing = client.delete(f"/transactions/{tx_id}")
    assert del_missing.status_code == 404
    assert del_missing.json()["error"] == "not_found"


def test_calculate_summary_decimal_precision(client: TestClient, db_session: Session) -> None:
    """Verify summary calculation avoids floating-point drift (e.g., 0.10 + 0.20 == 0.30)."""
    create_transaction(
        db_session,
        TransactionCreate(amount=Decimal("1000.10"), type=TransactionType.INCOME, category="salary"),
    )
    create_transaction(
        db_session,
        TransactionCreate(amount=Decimal("200.20"), type=TransactionType.INCOME, category="bonus"),
    )
    create_transaction(
        db_session,
        TransactionCreate(amount=Decimal("300.10"), type=TransactionType.EXPENSE, category="rent"),
    )
    create_transaction(
        db_session,
        TransactionCreate(amount=Decimal("50.20"), type=TransactionType.EXPENSE, category="food"),
    )

    summary = calculate_summary(db_session)
    assert summary.total_income == Decimal("1200.30")
    assert summary.total_expenses == Decimal("350.30")
    assert summary.net_balance == Decimal("850.00")
    assert summary.transaction_count == 4

    for path in ("/transactions/summary", "/summary"):
        resp = client.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(str(data["total_income"])) == Decimal("1200.30")
        assert Decimal(str(data["total_expenses"])) == Decimal("350.30")
        assert Decimal(str(data["net_balance"])) == Decimal("850.00")
        assert data["transaction_count"] == 4


def test_validation_rejects_invalid_inputs(client: TestClient) -> None:
    """Verify negative/zero amounts, >2 decimal places, invalid types, and blank categories fail with 422."""
    invalid_payloads = [
        {"amount": "0.00", "type": "expense", "category": "food"},
        {"amount": "-10.50", "type": "expense", "category": "food"},
        {"amount": "12.345", "type": "expense", "category": "food"},
        {"amount": "20.00", "type": "transfer", "category": "food"},
        {"amount": "20.00", "type": "expense", "category": "   "},
        {"type": "expense", "category": "food"},
    ]

    for payload in invalid_payloads:
        resp = client.post("/transactions", json=payload)
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"] == "validation_error"
        assert "details" in body

