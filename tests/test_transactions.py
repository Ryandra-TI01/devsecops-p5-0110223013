"""Comprehensive transaction CRUD, retrieval, filtering, and deletion tests."""

from decimal import Decimal

from fastapi.testclient import TestClient


def test_create_income_transaction(client: TestClient) -> None:
    """Verify successful creation of an income transaction."""
    payload = {
        "amount": "3500.50",
        "type": "income",
        "category": "freelance",
        "description": "Consulting project milestone 1",
    }
    response = client.post("/transactions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert Decimal(str(data["amount"])) == Decimal("3500.50")
    assert data["type"] == "income"
    assert data["category"] == "freelance"
    assert data["description"] == "Consulting project milestone 1"
    assert "created_at" in data


def test_create_expense_transaction_minimal(client: TestClient) -> None:
    """Verify creating an expense without optional description."""
    payload = {
        "amount": "12.00",
        "type": "expense",
        "category": "coffee",
    }
    response = client.post("/transactions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert Decimal(str(data["amount"])) == Decimal("12.00")
    assert data["type"] == "expense"
    assert data["category"] == "coffee"
    assert data["description"] is None


def test_get_existing_transaction_by_id(client: TestClient) -> None:
    """Verify fetching an existing transaction returns the exact record."""
    created = client.post(
        "/transactions",
        json={"amount": "99.99", "type": "expense", "category": "books"},
    ).json()

    response = client.get(f"/transactions/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_nonexistent_transaction_returns_404(client: TestClient) -> None:
    """Verify retrieving a non-existent transaction returns structured 404."""
    response = client.get("/transactions/9999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "not_found"
    assert "9999" in body["message"]


def test_list_transactions_empty(client: TestClient) -> None:
    """Verify listing transactions on an empty database returns an empty list."""
    response = client.get("/transactions")
    assert response.status_code == 200
    assert response.json() == []


def test_list_transactions_sorted_by_id(client: TestClient) -> None:
    """Verify listing transactions returns all records ordered by ID ascending."""
    client.post("/transactions", json={"amount": "10.00", "type": "expense", "category": "snacks"})
    client.post("/transactions", json={"amount": "50.00", "type": "income", "category": "gift"})
    client.post("/transactions", json={"amount": "30.00", "type": "expense", "category": "transport"})

    response = client.get("/transactions")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert [item["id"] for item in items] == [1, 2, 3]


def test_filter_transactions_by_type(client: TestClient) -> None:
    """Verify filtering transactions by type returns only matching items."""
    client.post("/transactions", json={"amount": "100.00", "type": "income", "category": "salary"})
    client.post("/transactions", json={"amount": "25.00", "type": "expense", "category": "lunch"})
    client.post("/transactions", json={"amount": "40.00", "type": "expense", "category": "dinner"})

    # Filter income
    income_resp = client.get("/transactions", params={"type": "income"})
    assert income_resp.status_code == 200
    income_items = income_resp.json()
    assert len(income_items) == 1
    assert income_items[0]["type"] == "income"
    assert income_items[0]["category"] == "salary"

    # Filter expense
    expense_resp = client.get("/transactions", params={"type": "expense"})
    assert expense_resp.status_code == 200
    expense_items = expense_resp.json()
    assert len(expense_items) == 2
    assert all(item["type"] == "expense" for item in expense_items)


def test_filter_transactions_by_category_case_insensitive(client: TestClient) -> None:
    """Verify filtering by category matches regardless of casing."""
    client.post("/transactions", json={"amount": "60.00", "type": "expense", "category": "Groceries"})
    client.post("/transactions", json={"amount": "45.00", "type": "expense", "category": "utilities"})

    # Query lowercase
    resp_lower = client.get("/transactions", params={"category": "groceries"})
    assert resp_lower.status_code == 200
    assert len(resp_lower.json()) == 1
    assert resp_lower.json()[0]["category"] == "Groceries"

    # Query uppercase
    resp_upper = client.get("/transactions", params={"category": "GROCERIES"})
    assert resp_upper.status_code == 200
    assert len(resp_upper.json()) == 1


def test_filter_transactions_by_type_and_category(client: TestClient) -> None:
    """Verify combined filtering by both type and category."""
    client.post("/transactions", json={"amount": "200.00", "type": "income", "category": "refund"})
    client.post("/transactions", json={"amount": "20.00", "type": "expense", "category": "refund"})
    client.post("/transactions", json={"amount": "15.00", "type": "expense", "category": "coffee"})

    resp = client.get("/transactions", params={"type": "income", "category": "refund"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["type"] == "income"
    assert results[0]["category"] == "refund"


def test_delete_existing_transaction(client: TestClient) -> None:
    """Verify deleting a transaction returns 204 and removes the record."""
    create_resp = client.post(
        "/transactions",
        json={"amount": "18.50", "type": "expense", "category": "fuel"},
    )
    tx_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/transactions/{tx_id}")
    assert delete_resp.status_code == 204
    assert delete_resp.text == ""

    get_resp = client.get(f"/transactions/{tx_id}")
    assert get_resp.status_code == 404
    assert get_resp.json()["error"] == "not_found"


def test_delete_nonexistent_transaction_returns_404(client: TestClient) -> None:
    """Verify deleting a nonexistent transaction returns 404."""
    response = client.delete("/transactions/8888")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
    assert "8888" in response.json()["message"]


def test_database_isolation_between_tests(client: TestClient) -> None:
    """Verify each test function starts with a clean, isolated database."""
    response = client.get("/transactions")
    assert response.status_code == 200
    assert response.json() == []

