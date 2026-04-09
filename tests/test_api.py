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
