import pytest


def test_web_status_no_cards(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.text == "OK: No cards"


def test_web_cards_returns_html(client):
    response = client.get("/cards")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
