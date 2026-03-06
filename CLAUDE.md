# CLAUDE.md — AI Assistant Guide for my-cards

## Project Overview

**my-cards** is a minimal Flask web application for tracking named cards and when they were last used. Users can create cards, mark them as "used" (updating the timestamp), and delete them. The app is deployed via Docker and served by Gunicorn.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Web Framework | Flask 3.1.0 |
| Database | SQLite (via Python's `sqlite3`) |
| Frontend | Jinja2 templating + Bootstrap 5.3.3 (CDN) |
| Production Server | Gunicorn 23.0.0 (2 workers) |
| Containerization | Docker (multi-arch: `linux/amd64`, `linux/arm64`) |
| CI/CD | GitHub Actions → GitHub Container Registry (`ghcr.io`) |

---

## Repository Structure

```
my-cards/
├── app.py                  # Flask app: routes and application factory
├── database.py             # SQLite connection helpers and init CLI command
├── schema.sql              # Database schema (single `card` table)
├── requirements.txt        # Python dependencies (pinned versions)
├── Dockerfile              # Container build (python:3.9-slim base)
├── docker-entrypoint.sh    # Container startup: init DB if missing, then start Gunicorn
├── Procfile                # PaaS process definition: gunicorn app:app
├── templates/
│   └── cards.html          # Single Jinja2 template (Bootstrap UI + inline JS)
├── .github/
│   └── workflows/
│       └── docker-build.yml  # CI: multi-arch Docker build & push on push to main
├── .gitignore              # Excludes .venv, __pycache__, instance/
├── .dockerignore           # Excludes dev artifacts from Docker context
└── README.md               # User-facing setup and deployment docs
```

The `instance/` directory (excluded from git) holds `flaskr.sqlite` at runtime.

---

## Database Schema

```sql
CREATE TABLE card (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- **Single table**, no migrations framework.
- `name` must be unique (enforced at the application layer, not a DB constraint).
- Timestamps are stored as UTC; the application converts them to `America/Los_Angeles` for display.
- `sqlite3.register_converter("timestamp", ...)` in `database.py` deserializes stored timestamps into Python `datetime` objects automatically.

---

## API Routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/status` | Health check — returns card count and last-updated timestamp |
| `GET` | `/cards` | Render the main UI with all cards |
| `POST` | `/cards` | Create a new card (form field: `name`); no-ops if name is blank or duplicate |
| `POST` | `/cards/<id>` | Touch `updated_at` to current time (mark as used) |
| `DELETE` | `/cards/<id>` | Delete a card |

All mutating routes redirect to `GET /cards` on success. The frontend uses `fetch()` for `POST /<id>` and `DELETE /<id>`, then redirects manually.

---

## Key Code Conventions

### Flask app (`app.py`)

- Uses `instance_relative_config=True` so config lives in `instance/config.py` (not committed).
- Default `SECRET_KEY` is `"dev"` — **always override in production** via `instance/config.py` or environment variable.
- Database path: `instance/flaskr.sqlite` (Flask `instance_path` + filename).
- Timezone conversion uses Python's stdlib `zoneinfo` (requires Python 3.9+).
- All timestamps displayed in `America/Los_Angeles` time (`%m/%d %H:%M` format).

### Database layer (`database.py`)

- `get_db()` stores the connection on Flask's `g` object (one connection per request).
- `close_db()` is registered as a teardown function — connections close automatically.
- `sqlite3.Row` row factory is set so rows support both index and key access.
- `detect_types=sqlite3.PARSE_DECLTYPES` + a registered converter handles `TIMESTAMP` columns.
- Initialize the database with: `flask init-db`

### Frontend (`templates/cards.html`)

- Single-file template — no separate CSS/JS assets; Bootstrap loaded from CDN.
- Cards are ordered by `updated_at ASC` (least-recently-used first).
- "Use Card" and "Delete Card" buttons show `confirm()` dialogs before acting.
- On `fetch()` failure, an `alert()` is shown and the page reloads.
- Auto-refresh: if the tab has been hidden for ≥ 4 hours and becomes visible, `window.location.reload()` is called.

---

## Development Workflow

### Local Setup (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize the database
flask --app app.py init-db

# Run the dev server
flask --app app.py run
```

The app will be available at `http://127.0.0.1:5000/cards`.

### Local Setup (with Docker)

```bash
# Build
docker build -t my-cards .

# Run (persisting the database)
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance my-cards
```

### Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `FLASK_APP` | `app.py` | Set in Dockerfile |
| `FLASK_ENV` | `production` | Set in Dockerfile |
| `SECRET_KEY` | `"dev"` | Override in `instance/config.py` for production |

There is no `.env` file. Override config at runtime via environment variables or `instance/config.py`.

---

## Testing

There is currently **no test suite**. If adding tests:

- Use `pytest` with `pytest-flask` or Flask's built-in test client.
- Place test files in a `tests/` directory.
- Use an in-memory SQLite database for test isolation.
- Add `pytest` to `requirements.txt` (or a separate `requirements-dev.txt`).

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/docker-build.yml`) runs on every push to `main`:

1. Checks out the code.
2. Logs in to GitHub Container Registry (`ghcr.io`) using `GITHUB_TOKEN`.
3. Sets up Docker Buildx for multi-platform builds.
4. Builds and pushes a multi-arch image (`linux/amd64` + `linux/arm64`).
5. Caches layers using GitHub's Action Cache backend.

Image is published to: `ghcr.io/<owner>/my-cards:latest`

---

## Things to Watch Out For

- **`schema.sql` drops the table**: Running `flask init-db` (or the entrypoint script on a fresh container) executes `DROP TABLE IF EXISTS card` before creating the table. **Do not run this against a database with data you want to keep.**
- **No migrations**: Schema changes require manual SQL or re-initialization (data loss).
- **Uniqueness is app-enforced**: Duplicate card names are silently rejected (redirect, no error message shown to user).
- **No authentication**: The app has no login or access control — anyone who can reach the URL can manage cards.
- **`instance/` is gitignored**: The SQLite database file is never committed. Persist it via a Docker volume in production.
- **Bootstrap via CDN**: The UI requires internet access to load styles/scripts.
