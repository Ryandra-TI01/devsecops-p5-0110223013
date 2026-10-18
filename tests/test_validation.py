"""Tests for input validation, edge cases, and structured error responses."""

from decimal import Decimal
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.models import TransactionType
from app.schemas import TransactionCreate


def test_reject_zero_amount(client: TestClient) -> None:
    """Verify amount of 0.00 is rejected with 422 Unprocessable Content."""
    response = client.post(
        "/transactions",
        json={"amount": "0.00", "type": "expense", "category": "food"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"
    assert any("greater than zero" in str(d["msg"]) for d in data.get("details", []))


def test_reject_negative_amount(client: TestClient) -> None:
    """Verify negative amount is rejected with 422."""
    response = client.post(
        "/transactions",
        json={"amount": "-50.00", "type": "expense", "category": "food"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"
    assert any("greater than zero" in str(d["msg"]) for d in data.get("details", []))


def test_reject_more_than_two_decimal_places(client: TestClient) -> None:
    """Verify monetary amounts with >2 decimal places are rejected."""
    response = client.post(
        "/transactions",
        json={"amount": "10.999", "type": "expense", "category": "food"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"
    assert any("more than 2 decimal places" in str(d["msg"]) for d in data.get("details", []))


def test_reject_non_numeric_amount(client: TestClient) -> None:
    """Verify non-numeric string for amount is rejected."""
    response = client.post(
        "/transactions",
        json={"amount": "not-a-number", "type": "expense", "category": "food"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"


def test_reject_boolean_as_amount(client: TestClient) -> None:
    """Verify boolean value (True/False) for amount is explicitly rejected."""
    response = client.post(
        "/transactions",
        json={"amount": True, "type": "expense", "category": "food"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"


def test_reject_invalid_transaction_type(client: TestClient) -> None:
    """Verify unsupported transaction types (e.g. 'transfer', 'credit') are rejected."""
    for invalid_type in ("transfer", "credit", "debit", "other"):
        response = client.post(
            "/transactions",
            json={"amount": "20.00", "type": invalid_type, "category": "food"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"


def test_reject_empty_or_whitespace_category(client: TestClient) -> None:
    """Verify empty or whitespace-only category string is rejected."""
    for empty_cat in ("", "   ", "\t\n"):
        response = client.post(
            "/transactions",
            json={"amount": "20.00", "type": "expense", "category": empty_cat},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"


def test_reject_missing_required_fields(client: TestClient) -> None:
    """Verify omitting required fields (amount, type, category) fails with 422."""
    # Missing amount
    resp1 = client.post("/transactions", json={"type": "income", "category": "salary"})
    assert resp1.status_code == 422

    # Missing type
    resp2 = client.post("/transactions", json={"amount": "100.00", "category": "salary"})
    assert resp2.status_code == 422

    # Missing category
    resp3 = client.post("/transactions", json={"amount": "100.00", "type": "income"})
    assert resp3.status_code == 422


def test_reject_malformed_json_body(client: TestClient) -> None:
    """Verify sending malformed raw JSON produces structured 422 response."""
    response = client.post(
        "/transactions",
        content="this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"


def test_reject_extra_fields_forbidden(client: TestClient) -> None:
    """Verify extra payload fields are rejected to prevent mass-assignment."""
    payload = {
        "amount": "50.00",
        "type": "expense",
        "category": "dinner",
        "unexpected_extra_field": "exploit",
    }
    response = client.post("/transactions", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"


def test_reject_invalid_transaction_id_path(client: TestClient) -> None:
    """Verify non-integer or zero/negative ID in path fails validation."""
    resp_zero = client.get("/transactions/0")
    assert resp_zero.status_code == 422

    resp_neg = client.get("/transactions/-5")
    assert resp_neg.status_code == 422

    resp_str = client.get("/transactions/abc")
    assert resp_str.status_code == 422


def test_pydantic_schema_direct_validation() -> None:
    """Unit test Pydantic schema validation directly."""
    with pytest.raises(ValidationError):
        TransactionCreate(amount=Decimal("0.00"), type=TransactionType.EXPENSE, category="test")

    with pytest.raises(ValidationError):
        TransactionCreate(amount=Decimal("-1.00"), type=TransactionType.EXPENSE, category="test")

    with pytest.raises(ValidationError):
        TransactionCreate(amount=Decimal("1.999"), type=TransactionType.EXPENSE, category="test")

