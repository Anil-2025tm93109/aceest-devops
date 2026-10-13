# ACEest Fitness & Performance

[![CI](https://github.com/Anil-2025tm93109/aceest-devops/actions/workflows/main.yml/badge.svg)](https://github.com/Anil-2025tm93109/aceest-devops/actions/workflows/main.yml)

A Flask REST API for **ACEest Fitness & Gym**, built for the *Introduction to DevOps* assignment.
It manages clients, training programs, weekly progress, workouts, body metrics, BMI and
memberships, and ships with a complete DevOps toolchain: Git/GitHub, Pytest, Docker,
GitHub Actions and Jenkins.

## Contents

- [Features](#features)
- [Project structure](#project-structure)
- [Local setup](#local-setup)
- [API reference](#api-reference)
- [Running the tests manually](#running-the-tests-manually)
- [Docker](#docker)
- [CI/CD overview](#cicd-overview)
- [Git workflow](#git-workflow)
- [Design notes and limitations](#design-notes-and-limitations)

## Features

The API grew version by version from the original ACEest desktop prototypes (v1.0 to v3.2.4):

| Prototype version | What it added | API equivalent |
|---|---|---|
| 1.0 / 1.1 | Programs with workout and diet plans, calorie estimate | `/programs`, `/clients` |
| 2.0 | Client records, weekly adherence | `/clients/<name>`, `/progress` |
| 2.2 | Goals, workouts, exercises, body metrics, BMI | `/workouts`, `/metrics`, `/bmi` |
| 3.x | Membership, program generator, reports | `/membership`, `/generate-program`, `/report` |

## Project structure

```text
.
├── app.py                  # Flask application
├── requirements.txt        # Runtime dependencies (Flask, gunicorn)
├── requirements-dev.txt    # Adds pytest and ruff for development and CI
├── tests/test_app.py       # Pytest suite (63 tests)
├── Dockerfile              # Multi-stage build: base, test, runtime
├── .dockerignore
├── Jenkinsfile             # Jenkins pipeline definition
└── .github/workflows/main.yml   # GitHub Actions pipeline
```

## Local setup

Requirements: Python 3.9 or newer and Git.

```bash
git clone https://github.com/Anil-2025tm93109/aceest-devops.git
cd aceest-devops

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements-dev.txt
python app.py
```

The API is now available at `http://localhost:5000`. Check it:

```bash
curl http://localhost:5000/health
```

`python app.py` uses Flask's development server. To run it the way the container does:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 app:app
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application status |
| GET | `/health` | Health check |
| GET | `/programs` | List programs with calorie factors, workouts and diets |
| GET | `/programs/<name>` | One program |
| GET | `/clients` | List clients, sorted by name |
| POST | `/clients` | Register a client |
| GET | `/clients/<name>` | Retrieve a client |
| PUT | `/clients/<name>` | Replace a client's profile (recalculates calories) |
| DELETE | `/clients/<name>` | Delete a client and all their records |
| POST, GET | `/clients/<name>/progress` | Log or list weekly adherence |
| GET | `/clients/<name>/progress/summary` | Average adherence and goal status |
| POST, GET | `/clients/<name>/workouts` | Log or list workouts with exercises |
| POST, GET | `/clients/<name>/metrics` | Log or list weight, waist and body fat |
| GET | `/clients/<name>/metrics/weight-trend` | Weight series and total change |
| GET | `/clients/<name>/bmi` | BMI, category and risk note (needs `height`) |
| GET | `/clients/<name>/membership` | Membership status (`?as_of=YYYY-MM-DD` optional) |
| POST, GET | `/clients/<name>/generate-program` | Generate or fetch a training plan |
| GET | `/clients/<name>/report` | Combined client report |

Client fields: `name`, `age`, `weight` and `program` are required. `height` (cm), `target_weight`,
`target_adherence` (1 to 100) and `membership_expiry` (`YYYY-MM-DD`) are optional.
Invalid input returns `400`, unknown clients `404`, and duplicate names `409`.

Example:

```bash
curl -X POST http://localhost:5000/clients \
  -H "Content-Type: application/json" \
  -d '{"name":"Anil","age":22,"weight":70,"height":175,"program":"Muscle Gain (MG)","membership_expiry":"2026-12-31"}'

curl http://localhost:5000/clients/Anil/bmi
curl "http://localhost:5000/clients/Anil/membership?as_of=2026-10-13"
```

## Running the tests manually

With the virtual environment active and `requirements-dev.txt` installed:

```bash
pytest -v                          # run the whole suite
pytest -v -k membership            # run only tests whose name contains "membership"
ruff check app.py tests            # lint
python -m compileall -q app.py tests   # syntax check
```

Run the same suite inside Docker, exactly as the pipelines do:

```bash
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

The suite uses Flask's test client, so no server needs to be running. It covers validation
and error paths (`400`, `404`, `409`) as well as the calculations: calories, BMI categories,
adherence averages, weight trends, membership dates and plan generation.

## Docker

The `Dockerfile` has three stages:

| Stage | Purpose |
|---|---|
| `base` | `python:3.11-slim` plus runtime dependencies only |
| `test` | Adds pytest, ruff and the tests; used by CI and Jenkins |
| `runtime` | Final image: only `app.py`, non-root user, health check (default target) |

Build and run:

```bash
docker build -t aceest-fitness:1.0 .
docker run -d --name aceest-container -p 5001:5000 aceest-fitness:1.0

curl http://localhost:5001/health
docker ps            # STATUS shows "healthy" once the health check passes

docker rm -f aceest-container
```

Port 5001 is used on the host in case port 5000 is already taken.

Image design choices: slim base image, no test or dev tools in the final image, a non-root
user (`uid 10001`), a built-in `HEALTHCHECK`, and gunicorn instead of the Flask development
server. Gunicorn runs **one worker with four threads** on purpose, because client data is held
in process memory and several worker processes would each see different data.

## CI/CD overview

Two pipelines validate every change. They build from the same `Dockerfile`, so a result in one
can be reproduced in the other.

### GitHub Actions (`.github/workflows/main.yml`)

Runs on every `push` and `pull_request`.

```text
Build & Lint                           Docker Build & Test (needs Build & Lint)
  checkout                               build image, target "test"
  set up Python 3.11 (pip cache)         run pytest INSIDE the container
  install requirements-dev.txt           build runtime image
  compileall syntax check                start container, check /health
  ruff lint                              check the container is non-root
```

The second job only starts if the first passes, so syntax or lint errors fail fast and
cheaply. Concurrent runs for the same branch are cancelled when a newer push arrives.

### Jenkins (`Jenkinsfile`)

A declarative pipeline for the controlled **BUILD** phase, defined as code in this repository:

```text
Checkout -> Clean Build -> Lint -> Unit Tests -> Build Runtime Image -> Smoke Test
```

- **Checkout** pulls the latest commit from GitHub.
- **Clean Build** builds the test image with `--no-cache`, so nothing stale is reused.
- **Lint** and **Unit Tests** run inside that image, so Jenkins needs only Docker, not Python.
- **Smoke Test** starts the runtime image and waits for its health check to report `healthy`.
  It also fails the build if the container runs as root.

Jenkins setup:

1. Create a **Pipeline** job.
2. Under *Pipeline*, choose **Pipeline script from SCM**, set SCM to **Git**, and use the
   repository URL `https://github.com/Anil-2025tm93109/aceest-devops.git`.
3. Set the branch to `*/main` and the script path to `Jenkinsfile`.
4. Optionally enable **Poll SCM** (for example `H/5 * * * *`) to build new commits automatically.
5. The Jenkins user must be allowed to run `docker`.

### How the two fit together

| | GitHub Actions | Jenkins |
|---|---|---|
| When | Every push and pull request | On demand or on a poll of `main` |
| Role | Fast feedback before merging | Clean, from-scratch build in a controlled environment |
| Build cache | Used | Disabled (`--no-cache`) |
| Result | Check shown on the pull request | Console log and build status |

## Git workflow

- `main` is the integration branch. Changes reach it through pull requests only, and
  pull requests are merged only after the GitHub Actions checks pass.
- Branch prefixes describe the change: `feature/...`, `fix/...`, `infrastructure/...`, `docs/...`.
- Commit messages are short imperative sentences, for example
  *Add weekly progress tracking and client goals*.

Application features were delivered one pull request at a time:

| PR | Branch | Tests after merge |
|---|---|---|
| #1 | `feature/program-catalog-and-client-crud` | 24 |
| #2 | `feature/progress-tracking` | 35 |
| #3 | `feature/workouts-metrics-bmi` | 50 |
| #4 | `feature/membership-and-reports` | 63 |

## Design notes and limitations

- Data is stored **in memory** and is lost when the application restarts. This keeps the
  assignment focused on the DevOps toolchain. The earlier desktop prototypes used SQLite;
  a persistent store would be the natural next step.
- There is **no authentication**. The prototype's login screen stored plaintext passwords,
  so it was deliberately not carried over.
- `/clients/<name>/report` returns **JSON** instead of the prototype's PDF export, which avoids
  an extra dependency.
- Program generation is **deterministic** (the prototype used random choices), which makes
  it testable.
