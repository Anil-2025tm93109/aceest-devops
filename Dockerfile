# ---- base: runtime dependencies only ---------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt


# ---- test: adds dev tools and the test suite (used by CI and Jenkins) -------
FROM base AS test

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY app.py .
COPY tests ./tests

CMD ["pytest", "-v"]


# ---- runtime: small, non-root production image (default target) ------------
FROM base AS runtime

LABEL org.opencontainers.image.title="ACEest Fitness & Performance" \
      org.opencontainers.image.description="Flask API for ACEest Fitness & Gym" \
      org.opencontainers.image.source="https://github.com/Anil-2025tm93109/aceest-devops"

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home \
       --shell /usr/sbin/nologin app

COPY app.py .

USER app

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)"]

# One worker on purpose: client data lives in process memory, so several
# worker processes would each see different data. Threads share the memory.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "app:app"]
