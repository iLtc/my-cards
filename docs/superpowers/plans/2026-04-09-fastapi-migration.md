# FastAPI Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the Flask app to FastAPI, replacing server-side rendering with a fully client-side UI backed by a JSON API that both the web UI and a future mobile app consume.

**Architecture:** FastAPI serves two routers — a web router (`/status`, `/cards`) that returns plain text or an HTML shell, and an API router (`/api/*`) that returns JSON. `cards.html` is a static shell; all data fetching and mutations happen via `fetch()` calls to `/api/cards`. SQLAlchemy replaces raw SQLite for the data layer, with DB-level uniqueness enforcement on card names.

**Tech Stack:** FastAPI, SQLAlchemy (sync), Pydantic v2, Jinja2, Uvicorn, Gunicorn (production), pytest + httpx (tests)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `pyproject.toml` | Swap Flask for FastAPI + SQLAlchemy + Uvicorn |
| Rewrite | `app.py` | FastAPI entry point, lifespan, web + API routers |
| Rewrite | `database.py` | SQLAlchemy engine, SessionLocal, `get_db` dependency, `init_db` |
| Create | `models.py` | SQLAlchemy `Card` model |
| Create | `schemas.py` | Pydantic `CardCreate` + `CardResponse` |
| Rewrite | `templates/cards.html` | Static HTML shell + vanilla JS |
| Modify | `Dockerfile` | Remove Flask env vars, update startup command |
| Modify | `docker-entrypoint.sh` | Remove `flask init-db`, update gunicorn worker |
| Modify | `Procfile` | Update gunicorn command |
| Create | `tests/conftest.py` | pytest fixtures: in-memory DB, TestClient |
| Create | `tests/test_api.py` | API route tests |
| Create | `tests/test_web.py` | Web route tests |
| Delete | `schema.sql` | Replaced by SQLAlchemy `create_all` |

---

## Task 1: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

Replace the `dependencies` block:

```toml
[project]
name = "my-cards"
version = "0.1.0"
description = "Minimal Flask app for tracking named cards and when they were last used"
requires-python = ">=3.9"
dependencies = [
    "fastapi==0.115.12",
    "uvicorn[standard]==0.34.0",
    "sqlalchemy==2.0.40",
    "jinja2==3.1.6",
    "gunicorn==23.0.0",
]

[dependency-groups]
dev = [
    "pytest==8.3.5",
    "httpx==0.28.1",
]
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync
```

Expected: no errors, `.venv` updated with fastapi, sqlalchemy, uvicorn, httpx, pytest installed.

- [ ] **Step 3: Verify FastAPI importable**

```bash
uv run python -c "import fastapi; import sqlalchemy; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: swap flask for fastapi + sqlalchemy + uvicorn"
```

---

## Task 2: Data Layer

**Files:**
- Create: `models.py`
- Rewrite: `database.py`

- [ ] **Step 1: Create models.py**

```python
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Card(Base):
    __tablename__ = "card"
    __table_args__ = (UniqueConstraint("name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
```

- [ ] **Step 2: Rewrite database.py**

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instance/flaskr.sqlite")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    os.makedirs("instance", exist_ok=True)
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 3: Verify models import**

```bash
uv run python -c "from models import Card; from database import init_db; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add models.py database.py
git commit -m "feat: add sqlalchemy data layer"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `schemas.py`

- [ ] **Step 1: Create schemas.py**

```python
from datetime import datetime
from pydantic import BaseModel, field_serializer


class CardCreate(BaseModel):
    name: str


class CardResponse(BaseModel):
    id: int
    name: str
    updated_at: datetime

    @field_serializer("updated_at")
    def serialize_updated_at(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Verify schemas import**

```bash
uv run python -c "from schemas import CardCreate, CardResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add schemas.py
git commit -m "feat: add pydantic schemas"
```

---

## Task 4: FastAPI App Skeleton + Health Check Routes + Test Infrastructure

**Files:**
- Create: `app.py`
- Create: `tests/conftest.py`
- Create: `tests/test_web.py`
- Create: `tests/test_api.py` (health check test only)

- [ ] **Step 1: Write the failing tests**

Create `tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from database import get_db

SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    from app import app
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()
```

Create `tests/test_web.py`:

```python
def test_web_status_no_cards(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.text == "OK: No cards"


def test_web_cards_returns_html(client):
    response = client.get("/cards")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
```

Create `tests/test_api.py`:

```python
def test_api_status_no_cards(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert response.json()["cards_count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail (app doesn't exist yet)**

```bash
uv run pytest tests/ -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `app` doesn't exist yet.

- [ ] **Step 3: Create app.py**

```python
from contextlib import asynccontextmanager

from fastapi import Depends, Request
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import database
from database import get_db
from models import Card


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

web_router = APIRouter()
api_router = APIRouter(prefix="/api")


@web_router.get("/status", response_class=PlainTextResponse)
def web_status(db: Session = Depends(get_db)):
    count = db.query(Card).count()
    if count == 0:
        return "OK: No cards"
    last = db.query(Card).order_by(Card.updated_at.desc()).first()
    return f"OK: {count} cards, last updated at {last.updated_at.isoformat()}Z"


@web_router.get("/cards", response_class=HTMLResponse)
def get_cards(request: Request):
    return templates.TemplateResponse("cards.html", {"request": request})


@api_router.get("/status")
def api_status(db: Session = Depends(get_db)):
    count = db.query(Card).count()
    if count == 0:
        return {"status": "OK", "cards_count": 0}
    last = db.query(Card).order_by(Card.updated_at.desc()).first()
    return {
        "status": "OK",
        "cards_count": count,
        "last_updated_at": f"{last.updated_at.isoformat()}Z",
    }


app.include_router(web_router)
app.include_router(api_router)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/ -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/conftest.py tests/test_web.py tests/test_api.py
git commit -m "feat: add fastapi app skeleton with health check routes"
```

---

## Task 5: API Card Routes

**Files:**
- Modify: `app.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_api.py` with:

```python
def test_api_status_no_cards(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert response.json()["cards_count"] == 0


def test_api_status_with_cards(client):
    client.post("/api/cards", json={"name": "Visa"})
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["cards_count"] == 1
    assert "last_updated_at" in response.json()


def test_list_cards_empty(client):
    response = client.get("/api/cards")
    assert response.status_code == 200
    assert response.json() == []


def test_create_card(client):
    response = client.post("/api/cards", json={"name": "Visa"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Visa"
    assert "id" in data
    assert "updated_at" in data
    assert data["updated_at"].endswith("Z")


def test_create_card_empty_name(client):
    response = client.post("/api/cards", json={"name": ""})
    assert response.status_code == 422


def test_create_card_duplicate_name(client):
    client.post("/api/cards", json={"name": "Visa"})
    response = client.post("/api/cards", json={"name": "Visa"})
    assert response.status_code == 409


def test_list_cards_ordered_by_updated_at_asc(client):
    client.post("/api/cards", json={"name": "Visa"})
    client.post("/api/cards", json={"name": "Amex"})
    response = client.get("/api/cards")
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 2
    assert cards[0]["name"] == "Visa"
    assert cards[1]["name"] == "Amex"


def test_use_card(client):
    create_resp = client.post("/api/cards", json={"name": "Visa"})
    card_id = create_resp.json()["id"]
    original_updated_at = create_resp.json()["updated_at"]

    import time; time.sleep(1)

    response = client.post(f"/api/cards/{card_id}")
    assert response.status_code == 200
    assert response.json()["updated_at"] != original_updated_at


def test_use_card_not_found(client):
    response = client.post("/api/cards/999")
    assert response.status_code == 404


def test_delete_card(client):
    create_resp = client.post("/api/cards", json={"name": "Visa"})
    card_id = create_resp.json()["id"]

    response = client.delete(f"/api/cards/{card_id}")
    assert response.status_code == 204

    list_resp = client.get("/api/cards")
    assert list_resp.json() == []


def test_delete_card_not_found(client):
    response = client.delete("/api/cards/999")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify new tests fail**

```bash
uv run pytest tests/test_api.py -v
```

Expected: the new tests fail with 404 (routes not defined yet).

- [ ] **Step 3: Add card routes to app.py**

Add these imports at the top of `app.py` (replacing the existing import block):

```python
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import database
from database import get_db
from models import Card
from schemas import CardCreate, CardResponse
```

Add these routes after `api_status` in `app.py`, before `app.include_router(...)`:

```python
@api_router.get("/cards", response_model=list[CardResponse])
def list_cards(db: Session = Depends(get_db)):
    return db.query(Card).order_by(Card.updated_at.asc()).all()


@api_router.post("/cards", response_model=CardResponse, status_code=201)
def create_card(card: CardCreate, db: Session = Depends(get_db)):
    if not card.name.strip():
        raise HTTPException(status_code=422, detail="Card name cannot be empty")
    db_card = Card(name=card.name.strip())
    db.add(db_card)
    try:
        db.commit()
        db.refresh(db_card)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Card name already exists")
    return db_card


@api_router.post("/cards/{card_id}", response_model=CardResponse)
def use_card(card_id: int, db: Session = Depends(get_db)):
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(card)
    return card


@api_router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.delete(card)
    db.commit()
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_api.py
git commit -m "feat: add api card routes (list, create, use, delete)"
```

---

## Task 6: Frontend Rewrite

**Files:**
- Rewrite: `templates/cards.html`

- [ ] **Step 1: Rewrite templates/cards.html**

```html
<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>My Cards</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <style>
        .navbar { margin-bottom: 20px; }
        #loading-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(255,255,255,0.7);
            z-index: 9999;
            align-items: center;
            justify-content: center;
        }
        #loading-overlay.active { display: flex; }
    </style>
</head>

<body>
    <div id="loading-overlay">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>

    <nav class="navbar bg-body-tertiary">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">My Cards</span>
        </div>
    </nav>

    <div class="container">
        <div id="cards-list" class="row row-cols-1 g-3">
            <!-- Cards rendered here by JS -->
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
        crossorigin="anonymous"></script>
    <script>
        const loadingOverlay = document.getElementById('loading-overlay');
        const cardsList = document.getElementById('cards-list');

        function showLoading() { loadingOverlay.classList.add('active'); }
        function hideLoading() { loadingOverlay.classList.remove('active'); }

        function formatDate(utcString) {
            return new Intl.DateTimeFormat(undefined, {
                dateStyle: 'medium',
                timeStyle: 'short'
            }).format(new Date(utcString));
        }

        async function fetchCards() {
            showLoading();
            try {
                const response = await fetch('/api/cards');
                if (!response.ok) {
                    window.location.reload();
                    return;
                }
                const cards = await response.json();
                renderCards(cards);
            } catch (err) {
                window.location.reload();
            } finally {
                hideLoading();
            }
        }

        function renderCards(cards) {
            const addCardHtml = `
                <div class="col">
                    <div class="card">
                        <div class="card-body">
                            <div class="row g-3 align-items-center">
                                <div class="col-auto">
                                    <input type="text" id="new-card-name" placeholder="Card Name" class="form-control">
                                </div>
                                <div class="col-auto">
                                    <button onclick="addCard()" class="btn btn-primary">Add Card</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`;

            const cardsHtml = cards.map(card => `
                <div class="col">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${escapeHtml(card.name)}</h5>
                            <p class="card-text">Last used: ${formatDate(card.updated_at)}</p>
                            <button onclick="useCard(${card.id}, '${escapeHtml(card.name)}')" class="btn btn-primary">Use Card</button>
                            <button onclick="deleteCard(${card.id}, '${escapeHtml(card.name)}')" class="btn btn-danger">Delete Card</button>
                        </div>
                    </div>
                </div>`).join('');

            cardsList.innerHTML = cardsHtml + addCardHtml;
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.appendChild(document.createTextNode(str));
            return div.innerHTML;
        }

        async function addCard() {
            const input = document.getElementById('new-card-name');
            const name = input.value.trim();
            if (!name) return;

            showLoading();
            try {
                const response = await fetch('/api/cards', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name }),
                });
                if (response.status === 409) {
                    alert(`A card named "${name}" already exists.`);
                    return;
                }
                if (!response.ok) {
                    alert('Failed to add card. Please try again.');
                    return;
                }
            } finally {
                hideLoading();
            }
            await fetchCards();
        }

        async function useCard(id, name) {
            if (!confirm(`Are you sure you want to use the card ${name}?`)) return;

            showLoading();
            try {
                const response = await fetch(`/api/cards/${id}`, { method: 'POST' });
                if (!response.ok) {
                    alert('The request failed. Please try again.');
                    return;
                }
            } finally {
                hideLoading();
            }
            await fetchCards();
        }

        async function deleteCard(id, name) {
            if (!confirm(`Are you sure you want to delete the card ${name}?`)) return;

            showLoading();
            try {
                const response = await fetch(`/api/cards/${id}`, { method: 'DELETE' });
                if (!response.ok) {
                    alert('The request failed. Please try again.');
                    return;
                }
            } finally {
                hideLoading();
            }
            await fetchCards();
        }

        // Auto-refresh: on tab focus after ≥4 hours, re-fetch via AJAX.
        // If fetch fails, fall back to full page reload (e.g. Cloudflare session expired).
        (function () {
            const REFRESH_THRESHOLD = 4 * 60 * 60 * 1000;
            let lastActiveTime = Date.now();

            document.addEventListener('visibilitychange', function () {
                if (!document.hidden) {
                    if (Date.now() - lastActiveTime >= REFRESH_THRESHOLD) {
                        fetchCards();
                    }
                } else {
                    lastActiveTime = Date.now();
                }
            });
        })();

        // Initial load
        fetchCards();
    </script>
</body>

</html>
```

- [ ] **Step 2: Start dev server and manually verify**

```bash
uv run uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/cards` in a browser. Verify:
- Page loads and displays an empty card list with the "Add Card" input
- Add a card — it appears in the list
- Use a card — timestamp updates
- Delete a card — it disappears
- Timestamps display in the browser's local timezone

- [ ] **Step 3: Commit**

```bash
git add templates/cards.html
git commit -m "feat: rewrite frontend as client-side SPA using /api/cards"
```

---

## Task 7: Deployment Updates + Cleanup

**Files:**
- Modify: `Dockerfile`
- Modify: `docker-entrypoint.sh`
- Modify: `Procfile`
- Delete: `schema.sql`

- [ ] **Step 1: Update Dockerfile**

```dockerfile
FROM python:3.9-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN mkdir -p instance

RUN chmod +x docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["./docker-entrypoint.sh"]
```

(Removes `ENV FLASK_APP` and `ENV FLASK_ENV` — no longer needed.)

- [ ] **Step 2: Update docker-entrypoint.sh**

```bash
#!/bin/bash
set -e

exec uv run gunicorn --bind 0.0.0.0:5000 --workers 2 -k uvicorn.workers.UvicornWorker app:app
```

(Removes the `flask init-db` step — `init_db()` is now called automatically via FastAPI's lifespan on startup.)

- [ ] **Step 3: Update Procfile**

```
web: gunicorn --bind 0.0.0.0:5000 --workers 2 -k uvicorn.workers.UvicornWorker app:app
```

- [ ] **Step 4: Delete schema.sql**

```bash
git rm schema.sql
```

- [ ] **Step 5: Run full test suite to confirm nothing broke**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-entrypoint.sh Procfile
git commit -m "feat: update deployment config for fastapi + uvicorn worker"
```

- [ ] **Step 7: Update CLAUDE.md**

Update the Development Commands section in `CLAUDE.md`:

```markdown
## Development Commands

\`\`\`bash
# Install dependencies
uv sync

# Run dev server (http://127.0.0.1:8000/cards)
uv run uvicorn app:app --reload

# Docker
docker build -t my-cards .
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance my-cards
\`\`\`
```

And update the Architecture section to reflect the new files (`models.py`, `schemas.py`, no `schema.sql`).

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for fastapi migration"
```
