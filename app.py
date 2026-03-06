import os
import zoneinfo as zi
from flask import Flask, request, render_template, redirect, url_for, make_response
import database

from_tz = zi.ZoneInfo("UTC")
default_to_tz = zi.ZoneInfo("America/Los_Angeles")

ALLOWED_TIMEZONES = {
    "America/Los_Angeles": "Los Angeles",
    "Pacific/Honolulu": "Hawaii",
}

def get_to_tz():
    tz_name = request.cookies.get("timezone", "America/Los_Angeles")
    if tz_name not in ALLOWED_TIMEZONES:
        tz_name = "America/Los_Angeles"
    return zi.ZoneInfo(tz_name)

app = Flask(__name__, instance_relative_config=True)

app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY="dev",
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, "flaskr.sqlite"),
    )
app.config.from_pyfile("config.py", silent=True)

try:
    os.makedirs(app.instance_path)
except OSError:
    pass

database.init_app(app)

@app.route("/status")
def status():
    db = database.get_db()

    cards_count = db.execute("SELECT COUNT(*) FROM card").fetchone()[0]

    if cards_count == 0:
        return "OK: No cards"
    else:
        card_last_updated = db.execute("SELECT updated_at FROM card ORDER BY updated_at DESC LIMIT 1").fetchone()[0]
        to_tz = get_to_tz()
        return f"OK: {cards_count} cards, last updated at {card_last_updated.replace(tzinfo=from_tz).astimezone(to_tz)}"

@app.get("/cards")
def get_cards():
    to_tz = get_to_tz()
    db = database.get_db()
    cards = db.execute("SELECT * FROM card ORDER BY updated_at ASC").fetchall()
    return render_template("cards.html", cards=cards, from_tz=from_tz, to_tz=to_tz,
                           timezones=ALLOWED_TIMEZONES, current_tz=to_tz.key)

@app.post("/timezone")
def set_timezone():
    tz_name = request.form.get("timezone", "America/Los_Angeles")
    if tz_name not in ALLOWED_TIMEZONES:
        tz_name = "America/Los_Angeles"
    response = make_response(redirect(url_for("get_cards")))
    response.set_cookie("timezone", tz_name, max_age=60 * 60 * 24 * 365)
    return response

@app.post("/cards")
def create_card():
    card_name = request.form["name"]

    db = database.get_db()

    # if card_name is empty, redirect to the cards page
    if not card_name:
        return redirect(url_for("get_cards"))

    # if card_name is already in the database, redirect to the cards page
    if db.execute("SELECT * FROM card WHERE name = ?", (card_name,)).fetchone():
        return redirect(url_for("get_cards"))

    # add the card to the database
    db.execute("INSERT INTO card (name) VALUES (?)", (card_name,))
    db.commit()
    return redirect(url_for("get_cards"))

@app.post("/cards/<int:id>")
def update_card(id):
    db = database.get_db()
    db.execute("UPDATE card SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("get_cards"))

@app.delete("/cards/<int:id>")
def delete_card(id):
    db = database.get_db()
    db.execute("DELETE FROM card WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("get_cards"))
