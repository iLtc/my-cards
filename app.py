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
