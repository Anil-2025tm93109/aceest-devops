from flask import Flask, jsonify, request

app = Flask(__name__)

PROGRAMS = {
    "Fat Loss (FL)": {"calorie_factor": 22},
    "Muscle Gain (MG)": {"calorie_factor": 35},
    "Beginner (BG)": {"calorie_factor": 26},
}

clients = {}


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


@app.post("/clients")
def create_client():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    name = data.get("name")
    age = data.get("age")
    weight = data.get("weight")
    program = data.get("program")

    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "A valid name is required"}), 400

    if isinstance(age, bool) or not isinstance(age, int) or age <= 0:
        return jsonify({"error": "Age must be a positive integer"}), 400

    if (
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or weight <= 0
    ):
        return jsonify({"error": "Weight must be a positive number"}), 400

    if program not in PROGRAMS:
        return jsonify({"error": "Invalid fitness program"}), 400

    name = name.strip()

    if name in clients:
        return jsonify({"error": "Client already exists"}), 409

    client = {
        "name": name,
        "age": age,
        "weight": float(weight),
        "program": program,
        "calories": int(weight * PROGRAMS[program]["calorie_factor"]),
    }

    clients[name] = client
    return jsonify(client), 201


@app.get("/clients/<name>")
def get_client(name):
    client = clients.get(name)

    if client is None:
        return jsonify({"error": "Client not found"}), 404

    return jsonify(client), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
