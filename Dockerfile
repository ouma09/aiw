# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────
# Banking Agent — Dockerfile
# Follows the blueprint pattern (non-root user, slim base)
# ─────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── System setup ─────────────────────────────────────────────────
WORKDIR /app

# Create non-root user (mirrors blueprint's devengine user)
RUN addgroup --gid 10001 devengine && \
    adduser --uid 10001 --ingroup devengine --disabled-password --gecos "" devengine && \
    chown -R devengine:devengine /app

USER devengine

# ── Dependencies ──────────────────────────────────────────────────
# Copy only requirements first to leverage Docker layer caching
COPY --chown=devengine:devengine requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Application code ──────────────────────────────────────────────
COPY --chown=devengine:devengine . /app

# ── Runtime config ────────────────────────────────────────────────
# Env vars are injected at runtime via --env-file or -e flags
# Do NOT bake secrets into the image
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/devengine/.local/bin:${PATH}"

# ── Entry point ───────────────────────────────────────────────────
# Interactive CLI — run with: docker run -it --env-file .env banking-agent
CMD ["python", "-m", "agent"]
