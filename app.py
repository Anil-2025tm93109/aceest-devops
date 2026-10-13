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
workouts = {}
metrics = {}

WORKOUT_TYPES = ["Strength", "Hypertrophy", "Conditioning", "Mixed", "Mobility"]

WEEK_PATTERN = re.compile(r"^\d{4}-W\d{2}$")


def error(message, status):
    return jsonify({"error": message}), status


def reset_state():
    """Clear all in-memory data (used by the test suite)."""
    clients.clear()
    progress.clear()
    workouts.clear()
    metrics.clear()


def parse_date(value):
    """Return an ISO date string (YYYY-MM-DD) or None if invalid."""
    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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

    height = data.get("height")
    if height is not None:
        if not is_number(height) or not 50 <= height <= 280:
            return None, "Height must be a number between 50 and 280 cm"
        values["height"] = float(height)

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
    workouts.pop(name, None)
    metrics.pop(name, None)

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


def validate_exercise(item):
    if not isinstance(item, dict):
        return None, "Each exercise must be an object"

    ex_name = item.get("name")
    sets = item.get("sets", 3)
    reps = item.get("reps", 10)
    weight = item.get("weight", 0)

    if not isinstance(ex_name, str) or not ex_name.strip():
        return None, "Exercise name is required"

    for label, value in (("Sets", sets), ("Reps", reps)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return None, f"{label} must be a positive integer"

    if not is_number(weight) or weight < 0:
        return None, "Exercise weight must be zero or more"

    exercise = {
        "name": ex_name.strip(),
        "sets": sets,
        "reps": reps,
        "weight": float(weight),
    }
    return exercise, None


@app.post("/clients/<name>/workouts")
def log_workout(name):
    if name not in clients:
        return error("Client not found", 404)

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error("A JSON object is required", 400)

    workout_date = parse_date(data.get("date", date.today().isoformat()))

    if workout_date is None:
        return error("Date must be a valid YYYY-MM-DD value", 400)

    workout_type = data.get("workout_type")

    if workout_type not in WORKOUT_TYPES:
        return error("Workout type must be one of " + ", ".join(WORKOUT_TYPES), 400)

    duration = data.get("duration_min", 60)

    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        return error("Duration must be a positive integer", 400)

    notes = data.get("notes", "")

    if not isinstance(notes, str):
        return error("Notes must be text", 400)

    raw_exercises = data.get("exercises", [])

    if not isinstance(raw_exercises, list):
        return error("Exercises must be a list", 400)

    exercises = []
    for item in raw_exercises:
        exercise, problem = validate_exercise(item)
        if problem:
            return error(problem, 400)
        exercises.append(exercise)

    entries = workouts.setdefault(name, [])
    workout = {
        "id": len(entries) + 1,
        "date": workout_date,
        "workout_type": workout_type,
        "duration_min": duration,
        "notes": notes.strip(),
        "exercises": exercises,
    }
    entries.append(workout)
    return jsonify(workout), 201


@app.get("/clients/<name>/workouts")
def list_workouts(name):
    if name not in clients:
        return error("Client not found", 404)

    ordered = sorted(
        workouts.get(name, []),
        key=lambda w: (w["date"], w["id"]),
        reverse=True,
    )
    return jsonify(ordered), 200


@app.post("/clients/<name>/metrics")
def log_metrics(name):
    client = clients.get(name)

    if client is None:
        return error("Client not found", 404)

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error("A JSON object is required", 400)

    metric_date = parse_date(data.get("date", date.today().isoformat()))

    if metric_date is None:
        return error("Date must be a valid YYYY-MM-DD value", 400)

    weight = data.get("weight")
    waist = data.get("waist")
    bodyfat = data.get("bodyfat")

    if weight is None and waist is None and bodyfat is None:
        return error("Provide at least one of weight, waist or bodyfat", 400)

    for label, value in (("Weight", weight), ("Waist", waist)):
        if value is not None and (not is_number(value) or value <= 0):
            return error(f"{label} must be a positive number", 400)

    if bodyfat is not None and (not is_number(bodyfat) or not 0 < bodyfat < 100):
        return error("Bodyfat must be a percentage between 0 and 100", 400)

    entry = {
        "date": metric_date,
        "weight": float(weight) if weight is not None else None,
        "waist": float(waist) if waist is not None else None,
        "bodyfat": float(bodyfat) if bodyfat is not None else None,
    }
    metrics.setdefault(name, []).append(entry)

    if weight is not None:
        profile = {key: client[key] for key in client if key not in ("name", "calories")}
        profile["weight"] = float(weight)
        clients[name] = build_client(name, profile)

    return jsonify(entry), 201


@app.get("/clients/<name>/metrics")
def list_metrics(name):
    if name not in clients:
        return error("Client not found", 404)

    ordered = sorted(metrics.get(name, []), key=lambda m: m["date"])
    return jsonify(ordered), 200


@app.get("/clients/<name>/metrics/weight-trend")
def weight_trend(name):
    if name not in clients:
        return error("Client not found", 404)

    points = [
        m for m in sorted(metrics.get(name, []), key=lambda m: m["date"])
        if m["weight"] is not None
    ]
    trend = {
        "dates": [m["date"] for m in points],
        "weights": [m["weight"] for m in points],
        "change": None,
    }

    if len(points) >= 2:
        trend["change"] = round(points[-1]["weight"] - points[0]["weight"], 1)

    return jsonify(trend), 200


def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight", "Potential nutrient deficiency, low energy."
    if bmi < 25:
        return "Normal", "Low risk if active and strong."
    if bmi < 30:
        return "Overweight", "Moderate risk; focus on adherence and progressive activity."
    return "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."


@app.get("/clients/<name>/bmi")
def get_bmi(name):
    client = clients.get(name)

    if client is None:
        return error("Client not found", 404)

    if "height" not in client:
        return error("Client height is required to calculate BMI", 400)

    height_m = client["height"] / 100.0
    bmi = round(client["weight"] / (height_m * height_m), 1)
    category, risk = bmi_category(bmi)
    return jsonify({"name": name, "bmi": bmi, "category": category, "risk": risk}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
