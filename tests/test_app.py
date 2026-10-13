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


def add_client(client, **extra):
    response = client.post("/clients", json=dict(PROFILE, **extra))
    assert response.status_code == 201
    return response


def test_height_is_stored_and_validated(client):
    assert add_client(client, height=170).json["height"] == 170.0
    for bad in (10, 500, "tall", True):
        response = client.post(
            "/clients", json=dict(PROFILE, name="X" + str(bad), height=bad)
        )
        assert response.status_code == 400


def test_log_workout_with_exercises(client):
    add_client(client)
    response = client.post(
        "/clients/Test User/workouts",
        json={
            "date": "2026-10-01",
            "workout_type": "Strength",
            "duration_min": 45,
            "notes": "  heavy day ",
            "exercises": [{"name": "Squat", "sets": 5, "reps": 5, "weight": 80}],
        },
    )
    assert response.status_code == 201
    assert response.json["id"] == 1
    assert response.json["notes"] == "heavy day"
    assert response.json["exercises"][0]["weight"] == 80.0


def test_workout_defaults(client):
    add_client(client)
    response = client.post(
        "/clients/Test User/workouts", json={"workout_type": "Cardio"}
    )
    assert response.status_code == 400
    response = client.post(
        "/clients/Test User/workouts", json={"workout_type": "Mobility"}
    )
    assert response.status_code == 201
    assert response.json["duration_min"] == 60
    assert response.json["exercises"] == []


def test_workout_validation(client):
    add_client(client)
    url = "/clients/Test User/workouts"
    ok = {"workout_type": "Mixed"}
    assert client.post(url, json=dict(ok, date="01-10-2026")).status_code == 400
    assert client.post(url, json=dict(ok, duration_min=0)).status_code == 400
    assert client.post(url, json=dict(ok, notes=5)).status_code == 400
    assert client.post(url, json=dict(ok, exercises="squat")).status_code == 400
    assert client.post(url, json=dict(ok, exercises=["squat"])).status_code == 400
    assert client.post(url, json=dict(ok, exercises=[{"name": ""}])).status_code == 400
    assert client.post(
        url, json=dict(ok, exercises=[{"name": "Row", "sets": 0}])
    ).status_code == 400
    assert client.post(
        url, json=dict(ok, exercises=[{"name": "Row", "weight": -1}])
    ).status_code == 400
    assert client.post(url, data="nope").status_code == 400


def test_workouts_sorted_newest_first(client):
    add_client(client)
    url = "/clients/Test User/workouts"
    client.post(url, json={"workout_type": "Mixed", "date": "2026-09-01"})
    client.post(url, json={"workout_type": "Strength", "date": "2026-10-01"})
    client.post(url, json={"workout_type": "Mobility", "date": "2026-10-01"})
    dates = [(w["date"], w["workout_type"]) for w in client.get(url).json]
    assert dates == [
        ("2026-10-01", "Mobility"),
        ("2026-10-01", "Strength"),
        ("2026-09-01", "Mixed"),
    ]


def test_workouts_and_metrics_need_existing_client(client):
    assert client.get("/clients/Ghost/workouts").status_code == 404
    assert client.post(
        "/clients/Ghost/workouts", json={"workout_type": "Mixed"}
    ).status_code == 404
    assert client.get("/clients/Ghost/metrics").status_code == 404
    assert client.post("/clients/Ghost/metrics", json={"weight": 70}).status_code == 404
    assert client.get("/clients/Ghost/metrics/weight-trend").status_code == 404
    assert client.get("/clients/Ghost/bmi").status_code == 404


def test_log_metrics_updates_weight_and_calories(client):
    add_client(client, height=170)
    response = client.post(
        "/clients/Test User/metrics",
        json={"date": "2026-10-01", "weight": 68, "waist": 80, "bodyfat": 20},
    )
    assert response.status_code == 201
    updated = client.get("/clients/Test User").json
    assert updated["weight"] == 68.0
    assert updated["calories"] == 1768
    assert updated["height"] == 170.0


def test_metrics_without_weight_keep_client_weight(client):
    add_client(client)
    client.post("/clients/Test User/metrics", json={"waist": 82})
    assert client.get("/clients/Test User").json["weight"] == 70.0


def test_metrics_validation(client):
    add_client(client)
    url = "/clients/Test User/metrics"
    assert client.post(url, json={}).status_code == 400
    assert client.post(url, json={"weight": 0}).status_code == 400
    assert client.post(url, json={"waist": "wide"}).status_code == 400
    assert client.post(url, json={"bodyfat": 100}).status_code == 400
    assert client.post(url, json={"weight": 70, "date": "nope"}).status_code == 400
    assert client.post(url, data="nope").status_code == 400


def test_metrics_sorted_by_date(client):
    add_client(client)
    url = "/clients/Test User/metrics"
    client.post(url, json={"weight": 69, "date": "2026-10-05"})
    client.post(url, json={"weight": 70, "date": "2026-10-01"})
    assert [m["date"] for m in client.get(url).json] == ["2026-10-01", "2026-10-05"]


def test_weight_trend(client):
    add_client(client)
    url = "/clients/Test User/metrics"
    empty = client.get(url + "/weight-trend").json
    assert empty == {"dates": [], "weights": [], "change": None}
    client.post(url, json={"weight": 72, "date": "2026-10-01"})
    client.post(url, json={"waist": 80, "date": "2026-10-02"})
    client.post(url, json={"weight": 69.5, "date": "2026-10-10"})
    trend = client.get(url + "/weight-trend").json
    assert trend["weights"] == [72.0, 69.5]
    assert trend["change"] == -2.5


def test_bmi_categories(client):
    cases = [
        ("Under", 50, 175, "Underweight"),
        ("Normal", 70, 175, "Normal"),
        ("Over", 85, 175, "Overweight"),
        ("Obese", 110, 175, "Obese"),
    ]
    for name, weight, height, category in cases:
        client.post(
            "/clients",
            json=dict(PROFILE, name=name, weight=weight, height=height),
        )
        response = client.get(f"/clients/{name}/bmi")
        assert response.status_code == 200
        assert response.json["category"] == category
        assert response.json["risk"]


def test_bmi_value(client):
    add_client(client, height=175)
    assert client.get("/clients/Test User/bmi").json["bmi"] == 22.9


def test_bmi_requires_height(client):
    add_client(client)
    assert client.get("/clients/Test User/bmi").status_code == 400


def test_delete_client_removes_workouts_and_metrics(client):
    add_client(client)
    client.post("/clients/Test User/workouts", json={"workout_type": "Mixed"})
    client.post("/clients/Test User/metrics", json={"weight": 70})
    client.delete("/clients/Test User")
    add_client(client)
    assert client.get("/clients/Test User/workouts").json == []
    assert client.get("/clients/Test User/metrics").json == []


def test_membership_active(client):
    add_client(client, membership_expiry="2026-12-31")
    response = client.get("/clients/Test User/membership?as_of=2026-12-01")
    assert response.status_code == 200
    assert response.json["status"] == "Active"
    assert response.json["days_remaining"] == 30


def test_membership_expires_on_last_day_inclusive(client):
    add_client(client, membership_expiry="2026-12-31")
    response = client.get("/clients/Test User/membership?as_of=2026-12-31")
    assert response.json["status"] == "Active"
    assert response.json["days_remaining"] == 0


def test_membership_expired(client):
    add_client(client, membership_expiry="2026-01-01")
    response = client.get("/clients/Test User/membership?as_of=2026-02-01")
    assert response.json["status"] == "Expired"
    assert response.json["days_remaining"] == -31


def test_membership_not_set(client):
    add_client(client)
    response = client.get("/clients/Test User/membership")
    assert response.status_code == 200
    assert response.json["status"] == "No membership"
    assert response.json["days_remaining"] is None


def test_membership_validation(client):
    response = client.post(
        "/clients", json=dict(PROFILE, membership_expiry="31/12/2026")
    )
    assert response.status_code == 400
    add_client(client)
    assert client.get("/clients/Test User/membership?as_of=bad").status_code == 400
    assert client.get("/clients/Ghost/membership").status_code == 404


def test_generate_program_beginner_full_body(client):
    add_client(client)
    response = client.post(
        "/clients/Test User/generate-program", json={"experience": "Beginner"}
    )
    assert response.status_code == 201
    assert response.json["focus"] == "Full Body"
    assert len(response.json["days"]) == 3
    first = response.json["days"][0]
    assert first["day"] == "Monday"
    assert len(first["exercises"]) == 3
    assert first["exercises"][0] == {"exercise": "Push-Up", "sets": 3, "reps": 10}


def test_generate_program_focus_follows_program(client):
    add_client(client, name="Cut", program="Fat Loss (FL)")
    add_client(client, name="Bulk", program="Muscle Gain (MG)")
    cut = client.post(
        "/clients/Cut/generate-program", json={"experience": "advanced"}
    ).json
    bulk = client.post(
        "/clients/Bulk/generate-program", json={"experience": "intermediate"}
    ).json
    assert cut["focus"] == "Conditioning"
    assert len(cut["days"]) == 5
    assert bulk["focus"] == "Hypertrophy"
    assert len(bulk["days"]) == 4
    assert bulk["days"][0]["exercises"][0]["sets"] == 4


def test_generate_program_is_deterministic_and_stored(client):
    add_client(client)
    url = "/clients/Test User/generate-program"
    assert client.get(url).status_code == 404
    first = client.post(url, json={"experience": "beginner"}).json
    second = client.post(url, json={"experience": "beginner"}).json
    assert first == second
    assert client.get(url).json == first


def test_generate_program_validation(client):
    add_client(client)
    url = "/clients/Test User/generate-program"
    assert client.post(url, json={"experience": "expert"}).status_code == 400
    assert client.post(url, json={}).status_code == 400
    assert client.post(url, data="nope").status_code == 400
    assert client.post(
        "/clients/Ghost/generate-program", json={"experience": "beginner"}
    ).status_code == 404
    assert client.get("/clients/Ghost/generate-program").status_code == 404


def test_report_for_minimal_client(client):
    add_client(client)
    response = client.get("/clients/Test User/report?as_of=2026-10-13")
    assert response.status_code == 200
    report = response.json
    assert report["profile"]["name"] == "Test User"
    assert report["membership"]["status"] == "No membership"
    assert report["progress"]["weeks_logged"] == 0
    assert report["bmi"] is None
    assert report["workouts"] == {"sessions": 0, "total_minutes": 0}
    assert report["metrics"] == {"entries": 0, "latest": None}
    assert report["generated_program"] is None
    assert report["generated_on"] == "2026-10-13"


def test_report_for_full_client(client):
    add_client(
        client,
        height=175,
        membership_expiry="2026-12-31",
        target_adherence=70,
    )
    base = "/clients/Test User"
    client.post(base + "/progress", json={"adherence": 80, "week": "2026-W40"})
    client.post(base + "/workouts", json={"workout_type": "Mixed", "duration_min": 30})
    client.post(base + "/workouts", json={"workout_type": "Strength", "duration_min": 45})
    client.post(base + "/metrics", json={"weight": 69, "date": "2026-10-01"})
    client.post(base + "/metrics", json={"waist": 80, "date": "2026-10-09"})
    client.post(base + "/generate-program", json={"experience": "beginner"})

    report = client.get(base + "/report?as_of=2026-12-01").json
    assert report["membership"]["status"] == "Active"
    assert report["progress"]["adherence_target_met"] is True
    assert report["bmi"]["bmi"] == 22.5
    assert report["workouts"] == {"sessions": 2, "total_minutes": 75}
    assert report["metrics"]["entries"] == 1
    assert report["metrics"]["latest"]["date"] == "2026-10-09"
    assert report["generated_program"]["experience"] == "beginner"


def test_report_validation(client):
    add_client(client)
    assert client.get("/clients/Test User/report?as_of=bad").status_code == 400
    assert client.get("/clients/Ghost/report").status_code == 404


def test_delete_client_removes_generated_program(client):
    add_client(client)
    client.post(
        "/clients/Test User/generate-program", json={"experience": "beginner"}
    )
    client.delete("/clients/Test User")
    add_client(client)
    assert client.get("/clients/Test User/generate-program").status_code == 404
