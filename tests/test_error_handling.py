"""Tests for error handling, internal exception masking, and database utilities."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import create_app
from app.models import SqliteDecimal, TWO_PLACES


def test_http_exception_handler_structured_response() -> None:
    """Verify HTTPException produces a sanitized structured error body."""
    app = create_app()

    @app.get("/test-http-error")
    def trigger_http_error() -> None:
        raise HTTPException(status_code=403, detail="Access denied to resource.")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-http-error")
    assert response.status_code == 403
    data = response.json()
    assert data["error"] == "http_error"
    assert data["message"] == "Access denied to resource."


def test_unhandled_exception_masks_internal_traceback() -> None:
    """Verify unexpected internal exceptions do not leak stack traces or internal details."""
    app = create_app()

    @app.get("/test-crash")
    def trigger_crash() -> None:
        raise RuntimeError("Secret database connection string or internal trace")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-crash")
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "internal_server_error"
    assert data["message"] == "An unexpected internal error occurred."
    assert "Secret database connection string" not in response.text
    assert "RuntimeError" not in response.text


def test_sqlite_decimal_type_decorator_none_handling() -> None:
    """Verify SqliteDecimal handles None safely on bind and result."""
    decorator = SqliteDecimal()
    assert decorator.process_bind_param(None, None) is None
    assert decorator.process_result_value(None, None) is None


def test_default_get_db_generator() -> None:
    """Verify the default get_db generator yields a session and closes it."""
    generator = get_db()
    session = next(generator)
    assert session is not None
    with pytest.raises(StopIteration):
        next(generator)
