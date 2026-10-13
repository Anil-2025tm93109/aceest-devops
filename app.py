import re
from datetime import date

from flask import Flask, jsonify, request

app = Flask(__name__)

PROGRAMS = {
    "Fat Loss (FL)": {
        "calorie_factor": 22,
        "workout": [
            "Mon: Back Squat 5x5 + Core",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: Deadlift + Box Jumps",
            "Fri: Zone 2 Cardio 30min",
        ],
        "diet": [
            "Breakfast: Egg Whites + Oats",
            "Lunch: Grilled Chicken + Brown Rice",
            "Dinner: Fish Curry + Millet Roti",
            "Target: ~2000 kcal",
        ],
    },
    "Muscle Gain (MG)": {
        "calorie_factor": 35,
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10",
        ],
        "diet": [
            "Breakfast: Eggs + Peanut Butter Oats",
            "Lunch: Chicken Biryani",
            "Dinner: Mutton Curry + Rice",
            "Target: ~3200 kcal",
        ],
    },
    "Beginner (BG)": {
        "calorie_factor": 26,
        "workout": [
            "Full Body Circuit: Air Squats, Ring Rows, Push-ups",
            "Focus: Technique & Consistency",
        ],
        "diet": [
            "Balanced Tamil Meals: Idli / Dosa / Rice + Dal",
            "Protein Target: 120g/day",
        ],
    },
}

clients = {}
progress = {}

WEEK_PATTERN = re.compile(r"^\d{4}-W\d{2}$")


def error(message, status):
    return jsonify({"error": message}), status


def reset_state():
    """Clear all in-memory data (used by the test suite)."""
    clients.clear()
    progress.clear()


def validate_profile(data):
    """Validate age, weight and program. Returns (values, error_message)."""
    if not isinstance(data, dict):
        return None, "A JSON object is required"

    age = data.get("age")
    weight = data.get("weight")
    program = data.get("program")

    if isinstance(age, bool) or not isinstance(age, int) or age <= 0:
        return None, "Age must be a positive integer"

    if (
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or weight <= 0
    ):
        return None, "Weight must be a positive number"

    if program not in PROGRAMS:
        return None, "Invalid fitness program"

    values = {"age": age, "weight": float(weight), "program": program}

    target_weight = data.get("target_weight")
    if target_weight is not None:
        if (
            isinstance(target_weight, bool)
            or not isinstance(target_weight, (int, float))
            or target_weight <= 0
        ):
            return None, "Target weight must be a positive number"
        values["target_weight"] = float(target_weight)

    target_adherence = data.get("target_adherence")
    if target_adherence is not None:
        if (
            isinstance(target_adherence, bool)
            or not isinstance(target_adherence, int)
            or not 1 <= target_adherence <= 100
        ):
            return None, "Target adherence must be an integer from 1 to 100"
        values["target_adherence"] = target_adherence

    return values, None


def build_client(name, profile):
    factor = PROGRAMS[profile["program"]]["calorie_factor"]
    client = {"name": name}
    client.update(profile)
    client["calories"] = int(profile["weight"] * factor)
    return client


@app.get("/")
def home():
    return jsonify(
        {
            "application": "ACEest Fitness & Performance",
            "status": "running",
        }
    ), 200


@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.get("/programs")
def list_programs():
    return jsonify(PROGRAMS), 200


@app.get("/programs/<name>")
def get_program(name):
    program = PROGRAMS.get(name)

    if program is None:
        return error("Program not found", 404)

    return jsonify(dict(program, name=name)), 200


@app.get("/clients")
def list_clients():
    ordered = sorted(clients.values(), key=lambda c: c["name"])
    return jsonify(ordered), 200


@app.post("/clients")
def create_client():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error("A JSON object is required", 400)

    name = data.get("name")

    if not isinstance(name, str) or not name.strip():
        return error("A valid name is required", 400)

    profile, problem = validate_profile(data)

    if problem:
        return error(problem, 400)

    name = name.strip()

    if name in clients:
        return error("Client already exists", 409)

    client = build_client(name, profile)
    clients[name] = client
    return jsonify(client), 201


@app.get("/clients/<name>")
def get_client(name):
    client = clients.get(name)

    if client is None:
        return error("Client not found", 404)

    return jsonify(client), 200


@app.put("/clients/<name>")
def update_client(name):
    if name not in clients:
        return error("Client not found", 404)

    profile, problem = validate_profile(request.get_json(silent=True))

    if problem:
        return error(problem, 400)

    clients[name] = build_client(name, profile)
    return jsonify(clients[name]), 200


@app.delete("/clients/<name>")
def delete_client(name):
    if clients.pop(name, None) is None:
        return error("Client not found", 404)

    progress.pop(name, None)

    return jsonify({"message": "Client deleted"}), 200


def current_week():
    iso = date.today().isocalendar()
    return "{}-W{:02d}".format(iso[0], iso[1])


@app.post("/clients/<name>/progress")
def log_progress(name):
    if name not in clients:
        return error("Client not found", 404)

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error("A JSON object is required", 400)

    adherence = data.get("adherence")

    if (
        isinstance(adherence, bool)
        or not isinstance(adherence, int)
        or not 0 <= adherence <= 100
    ):
        return error("Adherence must be an integer from 0 to 100", 400)

    week = data.get("week", current_week())

    if not isinstance(week, str) or not WEEK_PATTERN.match(week):
        return error("Week must look like 2026-W42", 400)

    entry = {"week": week, "adherence": adherence}
    progress.setdefault(name, []).append(entry)
    return jsonify(entry), 201


@app.get("/clients/<name>/progress")
def get_progress(name):
    if name not in clients:
        return error("Client not found", 404)

    return jsonify(progress.get(name, [])), 200


@app.get("/clients/<name>/progress/summary")
def progress_summary(name):
    client = clients.get(name)

    if client is None:
        return error("Client not found", 404)

    entries = progress.get(name, [])
    summary = {
        "name": name,
        "weeks_logged": len(entries),
        "average_adherence": 0,
        "latest_adherence": None,
        "target_adherence": client.get("target_adherence"),
        "adherence_target_met": None,
        "target_weight": client.get("target_weight"),
        "weight_to_target": None,
    }

    if entries:
        average = round(sum(e["adherence"] for e in entries) / len(entries), 1)
        summary["average_adherence"] = average
        summary["latest_adherence"] = entries[-1]["adherence"]

        if summary["target_adherence"] is not None:
            summary["adherence_target_met"] = (
                average >= summary["target_adherence"]
            )

    if summary["target_weight"] is not None:
        summary["weight_to_target"] = round(
            client["weight"] - summary["target_weight"], 1
        )

    return jsonify(summary), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
