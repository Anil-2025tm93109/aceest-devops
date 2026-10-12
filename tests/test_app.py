import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from app import app, clients


@pytest.fixture
def client():
    app.config["TESTING"] = True
    clients.clear()

    with app.test_client() as test_client:
        yield test_client

    clients.clear()


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json["status"] == "running"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_list_programs(client):
    response = client.get("/programs")
    assert response.status_code == 200
    assert "Fat Loss (FL)" in response.json
    assert "Muscle Gain (MG)" in response.json
    assert "Beginner (BG)" in response.json


def test_create_client(client):
    response = client.post(
        "/clients",
        json={
            "name": "Test User",
            "age": 30,
            "weight": 70,
            "program": "Beginner (BG)",
        },
    )

    assert response.status_code == 201
    assert response.json["name"] == "Test User"
    assert response.json["calories"] == 1820


def test_reject_invalid_age(client):
    response = client.post(
        "/clients",
        json={
            "name": "Test User",
            "age": -1,
            "weight": 70,
            "program": "Beginner (BG)",
        },
    )

    assert response.status_code == 400


def test_reject_invalid_program(client):
    response = client.post(
        "/clients",
        json={
            "name": "Test User",
            "age": 30,
            "weight": 70,
            "program": "Invalid Program",
        },
    )

    assert response.status_code == 400


def test_get_missing_client(client):
    response = client.get("/clients/Unknown")
    assert response.status_code == 404


def test_reject_duplicate_client(client):
    data = {
        "name": "Test User",
        "age": 30,
        "weight": 70,
        "program": "Beginner (BG)",
    }

    first_response = client.post("/clients", json=data)
    second_response = client.post("/clients", json=data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
