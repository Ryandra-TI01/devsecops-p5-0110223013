"""FastAPI application initialization and global exception handlers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routes import router
from app.schemas import ErrorDetail
from app.services import TransactionNotFoundError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database schema on application startup."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="Expense Tracker API",
        description="REST API for managing income and expense transactions with exact Decimal precision.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @application.exception_handler(TransactionNotFoundError)
    async def transaction_not_found_handler(
        _request: Request,
        exc: TransactionNotFoundError,
    ) -> JSONResponse:
        error_body = ErrorDetail(
            error="not_found",
            message=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_body.model_dump(exclude_none=True),
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        detail_msg = exc.detail if isinstance(exc.detail, str) else "Request could not be processed."
        error_body = ErrorDetail(
            error="http_error",
            message=detail_msg,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body.model_dump(exclude_none=True),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        sanitized_details = [
            {
                "loc": list(err.get("loc", [])),
                "msg": str(err.get("msg", "Invalid value")),
                "type": str(err.get("type", "value_error")),
            }
            for err in exc.errors()
        ]
        error_body = ErrorDetail(
            error="validation_error",
            message="Request validation failed.",
            details=sanitized_details,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_body.model_dump(exclude_none=True),
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled application error: %s", type(exc).__name__)
        error_body = ErrorDetail(
            error="internal_server_error",
            message="An unexpected internal error occurred.",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body.model_dump(exclude_none=True),
        )

    application.include_router(router)
    return application


app = create_app()

