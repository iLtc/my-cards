# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**my-cards** is a FastAPI web app for tracking named cards and when they were last used. Users create cards, mark them as "used" (updating the timestamp), and delete them. Deployed via Docker with Gunicorn.

## Development Commands

```bash
# Install dependencies
uv sync

# Run dev server (http://127.0.0.1:8000/cards)
uv run uvicorn app:app --reload

# Add a dependency
uv add <package>

# Docker
docker build -t my-cards .
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance my-cards
```

No test suite exists. If adding tests, use `pytest` with FastAPI's TestClient (httpx) and SQLAlchemy fixtures with in-memory SQLite.

## Architecture

- **`app.py`** — All routes and FastAPI app setup. Web router (/status, /cards) and API router (/api/*). Single module, no blueprints.
- **`database.py`** — SQLAlchemy engine, SessionLocal, get_db() dependency, init_db().
- **`models.py`** — SQLAlchemy Card model.
- **`schemas.py`** — Pydantic CardCreate + CardResponse models.
- **`templates/cards.html`** — Single Jinja2 template with inline JS. Bootstrap 5.3.3 via CDN.
- **`instance/`** — Gitignored. Holds `flaskr.sqlite` (SQLite database file) at runtime.

## Key Design Details

- **Single table, no migrations.** Schema changes require manual SQL or destructive re-init.
- **Uniqueness is DB-enforced via UniqueConstraint.** Duplicate names return 409 Conflict.
- **Timestamps** stored as UTC in SQLite. Returned as UTC ISO strings by the API. Displayed in browser's local timezone via Intl.DateTimeFormat.
- **Frontend mutations** — All mutations use fetch() calls to /api/cards. The web UI is a static HTML shell — no server-side rendering.
- **Auto-refresh** — Auto-refresh on tab focus after ≥4 hours: re-fetches via AJAX, falls back to full page reload on error (e.g. Cloudflare session expired).
- **No authentication** — anyone who can reach the URL can manage cards.

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Health check (web) |
| GET | `/cards` | Main UI |
| GET | `/api/status` | Health check (API) |
| GET | `/api/cards` | List all cards |
| POST | `/api/cards` | Create card |
| POST | `/api/cards/{id}` | Mark card as used (touch `updated_at`) |
| DELETE | `/api/cards/{id}` | Delete card |

## CI/CD

GitHub Actions (`.github/workflows/docker-build.yml`) builds and pushes a multi-arch Docker image to `ghcr.io` on every push to `main`.
