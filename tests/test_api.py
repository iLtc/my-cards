def test_api_status_no_cards(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert response.json()["cards_count"] == 0
