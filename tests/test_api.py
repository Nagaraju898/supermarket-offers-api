import pytest
from app import create_app, db

@pytest.fixture()
def client(tmp_path):
    database = tmp_path / "test.db"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
        "JWT_SECRET": "test-secret-key-at-least-32-bytes-long",
        "SECRET_KEY": "test-secret-key-at-least-32-bytes-long",
    })
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()

def register(client, email="owner@example.com"):
    return client.post("/api/supermarkets", json={
        "name": "Fresh Mart", "email": email, "password": "safe-pass-123",
        "address": "Hyderabad, India", "phone": "9876543210"
    })

def token_for(client, email="owner@example.com"):
    response = client.post("/api/auth/login", json={
        "email": email, "password": "safe-pass-123"
    })
    return response.get_json()["access_token"]

def test_register_and_duplicate_email(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409

def test_password_is_required_and_long_enough(client):
    response = client.post("/api/supermarkets", json={
        "name": "Shop", "email": "shop@example.com", "password": "short", "address": "Somewhere"
    })
    assert response.status_code == 400

def test_create_offer_and_browse_current_offer(client):
    register(client)
    token = token_for(client)
    response = client.post("/api/supermarkets/1/offers", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "title": "Test deal", "description": "A sample deal", "discount_percent": 15,
        "start_date": "2020-01-01T00:00:00Z", "end_date": "2099-01-01T00:00:00Z"
    })
    assert response.status_code == 201
    browse = client.get("/api/offers")
    assert browse.status_code == 200
    assert browse.get_json()["total"] == 1
    assert browse.get_json()["offers"][0]["title"] == "Test deal"

def test_offer_creation_requires_authentication(client):
    register(client)
    response = client.post("/api/supermarkets/1/offers", json={
        "title": "Test deal", "discount_percent": 10,
        "start_date": "2026-01-01T00:00:00Z", "end_date": "2027-01-01T00:00:00Z"
    })
    assert response.status_code == 401

def test_invalid_discount_is_rejected(client):
    register(client)
    token = token_for(client)
    response = client.post("/api/supermarkets/1/offers", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "title": "Bad deal", "discount_percent": 150,
        "start_date": "2026-01-01T00:00:00Z", "end_date": "2027-01-01T00:00:00Z"
    })
    assert response.status_code == 400
