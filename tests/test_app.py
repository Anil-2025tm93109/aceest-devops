import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from app import app, reset_state


@pytest.fixture
def client():
    app.config["TESTING"] = True
    reset_state()

    with app.test_client() as test_client:
        yield test_client

    reset_state()


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


PROFILE = {
    "name": "Test User",
    "age": 30,
    "weight": 70,
    "program": "Beginner (BG)",
}


def test_program_detail(client):
    response = client.get("/programs/Fat Loss (FL)")
    assert response.status_code == 200
    assert response.json["name"] == "Fat Loss (FL)"
    assert response.json["calorie_factor"] == 22
    assert len(response.json["workout"]) == 5
    assert response.json["diet"][-1] == "Target: ~2000 kcal"


def test_program_detail_missing(client):
    assert client.get("/programs/Nope").status_code == 404


def test_all_programs_have_plans(client):
    for program in client.get("/programs").json.values():
        assert program["workout"]
        assert program["diet"]


def test_list_clients_sorted(client):
    client.post("/clients", json=dict(PROFILE, name="Zed"))
    client.post("/clients", json=dict(PROFILE, name="Amy"))
    response = client.get("/clients")
    assert response.status_code == 200
    assert [c["name"] for c in response.json] == ["Amy", "Zed"]


def test_list_clients_empty(client):
    assert client.get("/clients").json == []


def test_reject_non_json_body(client):
    response = client.post("/clients", data="not json")
    assert response.status_code == 400


def test_reject_blank_name(client):
    response = client.post("/clients", json=dict(PROFILE, name="   "))
    assert response.status_code == 400


def test_reject_invalid_weight(client):
    for bad in (0, -5, "heavy", True):
        response = client.post("/clients", json=dict(PROFILE, weight=bad))
        assert response.status_code == 400


def test_reject_boolean_age(client):
    response = client.post("/clients", json=dict(PROFILE, age=True))
    assert response.status_code == 400


def test_name_is_trimmed(client):
    response = client.post("/clients", json=dict(PROFILE, name="  Ravi  "))
    assert response.status_code == 201
    assert client.get("/clients/Ravi").status_code == 200


def test_get_client(client):
    client.post("/clients", json=PROFILE)
    response = client.get("/clients/Test User")
    assert response.status_code == 200
    assert response.json["program"] == "Beginner (BG)"


def test_update_client_recalculates_calories(client):
    client.post("/clients", json=PROFILE)
    response = client.put(
        "/clients/Test User",
        json={"age": 31, "weight": 80, "program": "Muscle Gain (MG)"},
    )
    assert response.status_code == 200
    assert response.json["age"] == 31
    assert response.json["calories"] == 2800
    assert client.get("/clients/Test User").json["calories"] == 2800


def test_update_missing_client(client):
    response = client.put("/clients/Ghost", json=PROFILE)
    assert response.status_code == 404


def test_update_rejects_invalid_data(client):
    client.post("/clients", json=PROFILE)
    response = client.put(
        "/clients/Test User",
        json={"age": 0, "weight": 80, "program": "Beginner (BG)"},
    )
    assert response.status_code == 400


def test_delete_client(client):
    client.post("/clients", json=PROFILE)
    assert client.delete("/clients/Test User").status_code == 200
    assert client.get("/clients/Test User").status_code == 404


def test_delete_missing_client(client):
    assert client.delete("/clients/Ghost").status_code == 404
