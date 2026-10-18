"""Database engine, session factory, and initialization utilities."""

import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///./expenses.db"


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative ORM models."""


def get_database_url() -> str:
    """Return the configured database URL from the environment or the default."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@lru_cache(maxsize=8)
def get_engine(database_url: str | None = None) -> Engine:
    """Create and cache a SQLAlchemy Engine for the given database URL.

    Configures SQLite-specific connection args (`check_same_thread=False`)
    so connections work reliably across FastAPI threads and TestClient runs.
    """
    resolved_url = database_url or get_database_url()
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {}

    if resolved_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if resolved_url in ("sqlite://", "sqlite:///:memory:"):
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(
        resolved_url,
        connect_args=connect_args,
        **engine_kwargs,
    )

    if resolved_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Return a configured SQLAlchemy sessionmaker bound to the active engine."""
    engine = get_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(database_url: str | None = None, engine: Engine | None = None) -> None:
    """Create all database tables registered on Base metadata."""
    # Import models locally so metadata is populated before create_all is called.
    from app import models  # noqa: F401

    target_engine = engine or get_engine(database_url)
    Base.metadata.create_all(bind=target_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

