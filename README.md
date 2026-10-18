# Expense Tracker API

A modular, lightweight, and decimal-safe REST API built with FastAPI, SQLAlchemy 2.x, Pydantic v2, and SQLite. Designed as a foundational backend application for a university DevSecOps pipeline assignment, emphasizing clean architecture, input validation, defensive error handling, automated testing, and static security analysis (SAST).

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Architecture & Project Structure](#architecture--project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration & Database Location](#configuration--database-location)
- [Local Execution](#local-execution)
- [API Documentation](#api-documentation)
- [Running Automated Tests & Coverage](#running-automated-tests--coverage)
- [Security Review (SAST)](#security-review-sast)
- [CI/CD Pipeline Overview (Planned)](#cicd-pipeline-overview-planned)

---

## Features

1. **Transaction Management (CRUD)**:
   - Create income and expense transactions (`POST /transactions`).
   - Retrieve transaction details by unique positive integer ID (`GET /transactions/{id}`).
   - List all transactions ordered by ID ascending (`GET /transactions`).
   - Filter transactions with optional query parameters by `type` (`income` or `expense`) and case-insensitive `category` (`GET /transactions?type=...&category=...`).
   - Delete transactions by ID with proper `204 No Content` status (`DELETE /transactions/{id}`).
2. **Decimal-Safe Financial Summary**:
   - Aggregates `total_income`, `total_expenses`, `net_balance`, and `transaction_count` via `GET /transactions/summary` and alias `GET /summary`.
   - Uses exact Python `Decimal` arithmetic and integer-cent database storage to prevent binary floating-point drift (e.g. `0.10 + 0.20 = 0.30`).
3. **Strict Validation & Defensive Security**:
   - Rejects non-positive (zero or negative) amounts and amounts with more than two decimal places.
   - Rejects invalid transaction types and empty/whitespace categories.
   - Forbids unknown/extra request body fields (`extra="forbid"`) to prevent mass assignment.
   - Returns structured, consistent JSON error responses (`404 Not Found`, `422 Unprocessable Content`, `500 Internal Server Error`).
   - Masks internal server exceptions so stack traces, library internals, or database errors never leak to API clients.
4. **Health Check**:
   - Readiness endpoint returning HTTP 200 (`GET /health`).

---

## Technology Stack

- **Language**: Python 3.11+ (tested on Python 3.12)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (0.143+) + [Uvicorn](https://www.uvicorn.org/) (ASGI server)
- **ORM & Database**: [SQLAlchemy 2.x](https://www.sqlalchemy.org/) + [SQLite](https://sqlite.org/) (parameterized queries, custom `SqliteDecimal` integer-cents type)
- **Data Validation & Schemas**: [Pydantic v2](https://docs.pydantic.dev/)
- **Testing**: [pytest](https://docs.pytest.org/), [pytest-cov](https://pytest-cov.readthedocs.io/), [HTTPX](https://www.python-httpx.org/) (`TestClient`)
- **Static Security Analysis (SAST)**: [Bandit](https://bandit.readthedocs.io/)

---

## Architecture & Project Structure

The project follows a **Layered Architecture (N-Tier)** separating concerns between presentation, validation, business logic, and data persistence:

```text
expense-tracker-api/
├── app/
│   ├── __init__.py           # Package version metadata
│   ├── database.py           # Engine, session factory, SQLite config, and get_db dependency
│   ├── main.py               # FastAPI app factory, lifespan hook, and structured exception handlers
│   ├── models.py             # SQLAlchemy ORM models, constraints, and SqliteDecimal type
│   ├── routes.py             # API route definitions and endpoint handlers
│   ├── schemas.py            # Pydantic v2 request/response schemas and input validators
│   └── services.py           # Business logic, query construction, and Decimal summary math
├── tests/
│   ├── __init__.py           # Test package initialization
│   ├── conftest.py           # Isolated in-memory SQLite and TestClient fixtures
│   ├── test_api.py           # End-to-end API smoke tests
│   ├── test_error_handling.py# Exception masking and database utility tests
│   ├── test_summary.py       # Exact Decimal financial summary calculation tests
│   ├── test_transactions.py  # Comprehensive transaction CRUD and filter tests
│   └── test_validation.py    # Negative, zero, malformed input, and schema validation tests
├── .gitignore                # Excludes caches, venvs, DBs, and reports
├── pytest.ini                # Pytest configuration and coverage flags
├── README.md                 # Project documentation
└── requirements.txt          # Pinned runtime and testing dependencies
```

---

## Prerequisites

- **Python**: Version `3.11` or `3.12` installed (`python3 --version`).
- **Git**: Installed for version control (`git --version`).
- Linux, macOS, or Windows (WSL / bash recommended).

---

## Installation & Setup

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd expense-tracker-api
   ```

2. **Create and activate a Python virtual environment**:
   ```bash
   # On Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows (Command Prompt):
   # python -m venv .venv
   # .venv\Scripts\activate.bat
   ```

3. **Install declared dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## Configuration & Database Location

The database connection string is configurable via the `DATABASE_URL` environment variable.

- **Default**: `sqlite:///./expenses.db` (creates an `expenses.db` file in the current working directory).
- **Custom Location / In-Memory**:
  ```bash
  # Example: Custom local SQLite path
  export DATABASE_URL="sqlite:////tmp/my_expenses.db"

  # Example: Pure in-memory SQLite (default used in automated tests)
  export DATABASE_URL="sqlite://"
  ```

Tables are automatically initialized on application startup via the FastAPI `lifespan` handler.

---

## Local Execution

Start the API server locally using Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

*(Alternatively, without activating the virtual environment: `.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`)*

The server will start at `http://127.0.0.1:8000`.

### Health Check

Verify the API is running:
```bash
curl -X GET "http://127.0.0.1:8000/health"
# Response: {"status":"ok","service":"expense-tracker-api"}
```

---

## API Documentation

When the application is running locally, interactive API documentation is available out of the box:

- **Swagger UI (Interactive)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI (Alternative)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON Specification**: `http://127.0.0.1:8000/openapi.json`

---

## Running Automated Tests & Coverage

Tests use an isolated, in-memory SQLite database (`sqlite://`) managed by pytest fixtures in `tests/conftest.py`. Executing tests will **never** modify or overwrite your local developer database (`expenses.db`).

### Run all tests with code coverage:

```bash
pytest
```
*(Or explicitly `.venv/bin/pytest`)*

Coverage settings in `pytest.ini` automatically generate:
- Terminal coverage report with missing lines.
- `coverage.xml` for CI/CD Quality Gate integration.

### Run specific test modules:

```bash
pytest tests/test_transactions.py -v
pytest tests/test_summary.py -v
pytest tests/test_validation.py -v
pytest tests/test_error_handling.py -v
```

---

## Security Review (SAST)

Static Application Security Testing (SAST) is performed using **Bandit**:

```bash
# Run Bandit across application source code:
bandit -r app

# Run with verbose output:
bandit -r app -v

# Export report to HTML (for visual browser inspection):
bandit -r app -f html -o bandit_report.html
```

---

## CI/CD DevSecOps Pipeline

The repository includes an automated DevSecOps workflow defined in [`.github/workflows/devsecops.yml`](.github/workflows/devsecops.yml), configured to enforce code quality, test reliability, and static security checks on every code change.

### Trigger Conditions

The pipeline triggers automatically on:
- **Push** to the `main` branch.
- **Pull Request** targeting the `main` branch.

### Pipeline Architecture

```text
[ Trigger: Push / PR to main ]
              │
              ▼
    ┌───────────────────┐
    │     Job: build    │  ──> Checkout, Python 3.12, Install dependencies,
    └─────────┬─────────┘      Execute pytest suite & generate coverage.xml artifact
              │
              │ (needs: build)
              ▼
    ┌───────────────────┐
    │  Job: sast-scan   │  ──> Download coverage.xml artifact,
    │                   │      1. Bandit SAST scan (Python-specific vulnerabilities)
    │                   │      2. SonarCloud Scan (code smells, bugs, vulnerabilities)
    │                   │      3. SonarCloud Quality Gate check (blocks merge on failure)
    └───────────────────┘
```

### Jobs & Stages Overview

1. **`build` Job (`runs-on: ubuntu-latest`)**:
   - Checks out repository source code via `actions/checkout@v4`.
   - Sets up Python 3.12 with pip dependency caching (`actions/setup-python@v5`).
   - Installs production and test dependencies from `requirements.txt`.
   - Executes the full 39-test suite via `pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml`. Any test failure exits with a non-zero code and halts the pipeline immediately.
   - Preserves and uploads `coverage.xml` as a workflow artifact (`actions/upload-artifact@v4`) for use by the downstream security scanner.

2. **`sast-scan` Job (`runs-on: ubuntu-latest`, `needs: build`)**:
   - Dependent on `build` successfully passing.
   - Performs a full clone (`fetch-depth: 0`) required by SonarCloud for accurate blame and "New Code" tracking.
   - Downloads the `coverage.xml` artifact produced in the `build` job.
   - **Secondary SAST (Bandit)**: Executes `bandit -r app -v` to detect Python-specific security flaws (e.g., SQL injection, insecure imports, unsafe functions). If Bandit finds medium/high vulnerabilities, the job immediately terminates with a non-zero exit code.
   - **Primary SAST (SonarCloud)**: Runs `SonarSource/sonarqube-scan-action@v8` to analyze code complexity, duplicated code, security hotspots, and test coverage metrics.
   - **Quality Gate Enforcement**: Uses `sonarsource/sonarqube-quality-gate-action@v1.2.1` with a 5-minute timeout. The step actively polls SonarCloud's compute engine and fails the pipeline if the Quality Gate evaluation returns `ERROR` or `FAILED`.

### Quality Gate Behavior & Failure Semantics

The pipeline explicitly distinguishes between different failure modes:
- **Build/Test Failure**: If any unit test fails or dependencies cannot be installed in the `build` job, `build` fails, and `sast-scan` is skipped entirely.
- **Bandit SAST Failure**: If Bandit detects Python security violations, the scan step fails before SonarCloud analysis is reached.
- **SonarCloud Scanner Failure**: If SonarCloud credentials or connection parameters are invalid, the scan upload step fails.
- **Quality Gate Failure**: If the scan succeeds and uploads to SonarCloud, but the code fails SonarCloud's Quality Gate conditions (e.g., insufficient test coverage, unresolved security hotspots, or bugs on new code), the Quality Gate step fails with exit code 1.
- **Success**: Both `build` and `sast-scan` pass, and SonarCloud reports a status of `PASSED`.

### Required GitHub Secrets & Repository Setup

To enable SonarCloud analysis in GitHub Actions:

1. **SonarCloud Token**:
   - Go to [SonarCloud](https://sonarcloud.io/) > **My Account** > **Security**.
   - Generate a new user token.
   - In your GitHub repository: Navigate to **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
   - Name: `SONAR_TOKEN`
   - Value: `<your-sonarcloud-token>`

2. **SonarCloud Organization & Project Key**:
   - In GitHub repository **Settings** > **Secrets and variables** > **Actions** > **Variables** (or Secrets):
     - `SONAR_ORGANIZATION`: Your SonarCloud organization key (e.g., `my-github-username`).
     - `SONAR_PROJECT_KEY`: Your SonarCloud project key (defaults to `expense-tracker-api`).
   - Alternatively, edit [`sonar-project.properties`](sonar-project.properties) directly with your organization key:
     ```properties
     sonar.organization=your-organization-key
     sonar.projectKey=expense-tracker-api
     ```

### Manual Steps to Trigger the First Pipeline Run

1. Create a public repository on GitHub (e.g., `https://github.com/<your-username>/expense-tracker-api`).
2. Import/link your GitHub repository in [SonarCloud](https://sonarcloud.io/projects/create) and obtain your `SONAR_TOKEN` and organization key.
3. Configure the `SONAR_TOKEN` secret in your GitHub repository settings.
4. Add the GitHub remote and push your code:
   ```bash
   git remote add origin https://github.com/<your-username>/expense-tracker-api.git
   git branch -M main
   git push -u origin main
   ```
5. Navigate to the **Actions** tab in your GitHub repository to observe the `DevSecOps Pipeline` execution.

