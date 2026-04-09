# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**my-cards** is a Flask web app for tracking named cards and when they were last used. Users create cards, mark them as "used" (updating the timestamp), and delete them. Deployed via Docker with Gunicorn.

## Development Commands

```bash
# Install dependencies
uv sync

# Initialize database (WARNING: drops existing card table — destroys data)
uv run flask --app app.py init-db

# Run dev server (http://127.0.0.1:5000/cards)
uv run flask --app app.py run

# Add a dependency
uv add <package>

# Docker
docker build -t my-cards .
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance my-cards
```

No test suite exists. If adding tests, use `pytest` with Flask's test client and in-memory SQLite.

## Architecture

- **`app.py`** — All routes and Flask app setup. Single module, no blueprints.
- **`database.py`** — SQLite connection management via Flask's `g` object, plus `init-db` CLI command.
- **`schema.sql`** — Single `card` table. Starts with `DROP TABLE IF EXISTS` (destructive on re-run).
- **`templates/cards.html`** — Single Jinja2 template with inline JS. Bootstrap 5.3.3 via CDN.
- **`instance/`** — Gitignored. Holds `flaskr.sqlite` at runtime.

## Key Design Details

- **Single table, no migrations.** Schema changes require manual SQL or destructive re-init.
- **Uniqueness is app-enforced only** — duplicate card names are silently rejected (no DB constraint, no user-facing error).
- **Timestamps** stored as UTC in SQLite. Displayed in user's selected timezone (cookie `timezone`). Default: `America/Los_Angeles`. Allowed timezones are hardcoded in `ALLOWED_TIMEZONES` dict in `app.py`.
- **Timezone selection** — `POST /timezone` sets a cookie; `get_to_tz()` reads it on each request.
- **Frontend mutations** — "Use Card" and "Delete Card" use `fetch()` with `POST`/`DELETE`, then redirect via JS. The "Add Card" form uses a standard HTML form POST.
- **Auto-refresh** — If the browser tab has been hidden for ≥4 hours, the page reloads on focus.
- **No authentication** — anyone who can reach the URL can manage cards.

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Health check |
| GET | `/cards` | Main UI |
| POST | `/cards` | Create card (form field: `name`) |
| POST | `/cards/<id>` | Mark card as used (touch `updated_at`) |
| DELETE | `/cards/<id>` | Delete card |
| POST | `/timezone` | Set timezone preference cookie |

## CI/CD

GitHub Actions (`.github/workflows/docker-build.yml`) builds and pushes a multi-arch Docker image to `ghcr.io` on every push to `main`.
