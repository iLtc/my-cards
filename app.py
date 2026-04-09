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


app.include_router(web_router)
app.include_router(api_router)
