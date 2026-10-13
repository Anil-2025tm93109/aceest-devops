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


def test_goals_are_stored(client):
    response = client.post(
        "/clients",
        json=dict(PROFILE, target_weight=65, target_adherence=80),
    )
    assert response.status_code == 201
    assert response.json["target_weight"] == 65.0
    assert response.json["target_adherence"] == 80


def test_reject_invalid_goals(client):
    assert client.post(
        "/clients", json=dict(PROFILE, target_weight=-1)
    ).status_code == 400
    assert client.post(
        "/clients", json=dict(PROFILE, target_adherence=101)
    ).status_code == 400
    assert client.post(
        "/clients", json=dict(PROFILE, target_adherence=0)
    ).status_code == 400


def test_log_progress_with_explicit_week(client):
    client.post("/clients", json=PROFILE)
    response = client.post(
        "/clients/Test User/progress",
        json={"adherence": 85, "week": "2026-W10"},
    )
    assert response.status_code == 201
    assert response.json == {"week": "2026-W10", "adherence": 85}


def test_log_progress_defaults_to_current_week(client):
    client.post("/clients", json=PROFILE)
    response = client.post("/clients/Test User/progress", json={"adherence": 50})
    assert response.status_code == 201
    assert response.json["week"].startswith("20")
    assert "-W" in response.json["week"]


def test_log_progress_validation(client):
    client.post("/clients", json=PROFILE)
    url = "/clients/Test User/progress"
    assert client.post(url, json={"adherence": 101}).status_code == 400
    assert client.post(url, json={"adherence": -1}).status_code == 400
    assert client.post(url, json={"adherence": "high"}).status_code == 400
    assert client.post(url, json={"adherence": 50, "week": "bad"}).status_code == 400
    assert client.post(url, data="nope").status_code == 400


def test_progress_requires_existing_client(client):
    assert client.post(
        "/clients/Ghost/progress", json={"adherence": 50}
    ).status_code == 404
    assert client.get("/clients/Ghost/progress").status_code == 404
    assert client.get("/clients/Ghost/progress/summary").status_code == 404


def test_get_progress_lists_entries_in_order(client):
    client.post("/clients", json=PROFILE)
    url = "/clients/Test User/progress"
    client.post(url, json={"adherence": 60, "week": "2026-W01"})
    client.post(url, json={"adherence": 90, "week": "2026-W02"})
    response = client.get(url)
    assert [e["adherence"] for e in response.json] == [60, 90]


def test_progress_summary_without_data(client):
    client.post("/clients", json=PROFILE)
    summary = client.get("/clients/Test User/progress/summary").json
    assert summary["weeks_logged"] == 0
    assert summary["average_adherence"] == 0
    assert summary["latest_adherence"] is None
    assert summary["adherence_target_met"] is None


def test_progress_summary_with_goals(client):
    client.post(
        "/clients",
        json=dict(PROFILE, target_weight=65, target_adherence=75),
    )
    url = "/clients/Test User/progress"
    client.post(url, json={"adherence": 70, "week": "2026-W01"})
    client.post(url, json={"adherence": 90, "week": "2026-W02"})
    summary = client.get(url + "/summary").json
    assert summary["weeks_logged"] == 2
    assert summary["average_adherence"] == 80.0
    assert summary["latest_adherence"] == 90
    assert summary["adherence_target_met"] is True
    assert summary["weight_to_target"] == 5.0


def test_progress_target_not_met(client):
    client.post("/clients", json=dict(PROFILE, target_adherence=90))
    client.post(
        "/clients/Test User/progress",
        json={"adherence": 50, "week": "2026-W01"},
    )
    summary = client.get("/clients/Test User/progress/summary").json
    assert summary["adherence_target_met"] is False


def test_delete_client_removes_progress(client):
    client.post("/clients", json=PROFILE)
    client.post("/clients/Test User/progress", json={"adherence": 50})
    client.delete("/clients/Test User")
    client.post("/clients", json=PROFILE)
    assert client.get("/clients/Test User/progress").json == []
