# ACEest Fitness & Performance

A Flask-based fitness management application developed for the ACEest Fitness & Gym DevOps assignment.

## Features

- Health-check endpoint
- Fitness programs and calorie factors
- Client registration and retrieval
- Input validation and duplicate-client handling
- Automated tests using pytest
- Docker containerization

## Technology Stack

- Python
- Flask
- Pytest
- Docker
- Git and GitHub
- Jenkins
- GitHub Actions

## Local Setup

Clone the repository:

```bash
git clone https://github.com/Anil-2025tm93109/aceest-devops.git
cd aceest-devops
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
python app.py
```

The application runs on port 5000.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application status |
| GET | `/health` | Health check |
| GET | `/programs` | List fitness programs |
| POST | `/clients` | Register a client |
| GET | `/clients/<name>` | Retrieve a client |

### Example Client Registration

```bash
curl -X POST http://localhost:5000/clients \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","age":30,"weight":70,"program":"Beginner (BG)"}'
```

## Automated Testing

Run the test suite:

```bash
pytest -v
```

The tests cover application status, health, fitness programs, client creation, input validation, missing clients, and duplicate clients.

## Docker

Build the image:

```bash
docker build -t aceest-fitness:1.0 .
```

Run the container:

```bash
docker run -d --name aceest-container -p 5001:5000 aceest-fitness:1.0
```

Verify the application:

```bash
curl http://localhost:5001/health
curl http://localhost:5001/programs
```

Port 5001 is used on the host to avoid conflicts with applications already using port 5000.

## CI/CD

The planned CI/CD configuration uses GitHub Actions to validate the application, run tests, and build the Docker image on pushes and pull requests. Jenkins is used to pull the latest repository changes and perform a clean build.

## Limitations

Client records are stored in application memory and are lost when the application restarts. This implementation is intended as a DevOps assignment prototype, not a production deployment.
