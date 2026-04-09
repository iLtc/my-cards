# FastAPI Migration Design

**Date:** 2026-04-09

## Overview

Migrate the Flask web app to FastAPI to support a mobile app consuming the same card operations through a JSON API. The web UI is retained but moves from server-side rendering to a fully client-side architecture. The API becomes the single source of truth for all data.

## Architecture

Four Python files, one template:

```
app.py               — FastAPI entry point, mounts web + API routers
database.py          — SQLAlchemy engine + get_db() Depends() session
models.py            — SQLAlchemy Card model (replaces schema.sql)
schemas.py           — Pydantic request/response models
templates/cards.html — Static HTML shell + vanilla JS (no server-side data)
```

`schema.sql` is removed. Database initialization uses `Base.metadata.create_all()` called at app startup (or via a CLI command for explicit control).

## Routes

### Web router (no prefix)

| Method | Path     | Description               |
|--------|----------|---------------------------|
| GET    | `/status` | Health check (plain text) |
| GET    | `/cards`  | Serve static HTML shell   |

### API router (prefix `/api`)

| Method | Path               | Description                          |
|--------|--------------------|--------------------------------------|
| GET    | `/api/status`      | Health check (JSON)                  |
| GET    | `/api/cards`       | List all cards                       |
| POST   | `/api/cards`       | Create card `{"name": "..."}`        |
| POST   | `/api/cards/{id}`  | Mark card as used (touch updated_at) |
| DELETE | `/api/cards/{id}`  | Delete card                          |

**Removed:** `POST /timezone` and all cookie/timezone logic.

API responses return timestamps as UTC ISO strings (e.g. `"2026-04-09T12:00:00Z"`). The frontend formats them using the browser's local timezone via `Intl.DateTimeFormat`.

## Data Model

SQLAlchemy `Card` model replacing `schema.sql`:

```python
class Card(Base):
    __tablename__ = "card"
    id: int          # primary key, autoincrement
    name: str        # unique constraint (DB-enforced)
    updated_at: datetime  # default: UTC now, updated on "use"
```

**Change from today:** uniqueness is enforced at the DB level via `UniqueConstraint`. The API returns `409 Conflict` on duplicate name, rather than silently ignoring it.

### Pydantic Schemas

- `CardCreate` — request body for `POST /api/cards`: `{"name": "..."}`
- `CardResponse` — response for all card endpoints: `{"id": 1, "name": "...", "updated_at": "2026-04-09T12:00:00Z"}`

### Database Session

Flask's `g`-based `get_db()` is replaced with a FastAPI dependency:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Used in routes as `db: Session = Depends(get_db)`.

## Frontend

`cards.html` becomes a static HTML shell. On page load, JavaScript calls `GET /api/cards` and renders the card list. All mutations call the corresponding `/api/cards` endpoints via `fetch()`, then re-fetch the list to update the UI.

**Timezone:** The manual selector dropdown and cookie are removed. Timestamps are formatted client-side:

```js
new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
}).format(new Date(card.updated_at))
```

**Retained from today:**
- Bootstrap 5.3.3 via CDN
- Overall visual design
- On tab focus after ≥4 hours hidden: re-fetch cards via AJAX (no full page reload). Show a loading indicator during the fetch. If the fetch fails (e.g. Cloudflare session expired → 401/403), fall back to a full page reload so Cloudflare can trigger its login flow.

## Error Handling

| Scenario              | HTTP Status     |
|-----------------------|-----------------|
| Duplicate card name   | 409 Conflict    |
| Card ID not found     | 404 Not Found   |
| Empty name submitted  | 422 Unprocessable Entity (Pydantic validation) |

## Dependencies

New packages to add:
- `fastapi`
- `uvicorn[standard]` (replaces gunicorn for dev; gunicorn + uvicorn worker for production)
- `sqlalchemy`

Removed:
- `flask`

## Deployment

The Docker setup changes minimally: replace `gunicorn app:app` with `gunicorn app:app -k uvicorn.workers.UvicornWorker`. The `instance/` volume mount for SQLite stays the same.
