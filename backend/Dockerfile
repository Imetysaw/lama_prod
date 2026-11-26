# LaMa backend (Flask API)
#
# Build stage: compile the Python dependencies (mysqlclient needs a compiler and the
# MySQL/MariaDB client headers). The runtime stage only gets the resulting packages.
FROM python:3.13-slim-bookworm AS build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt


# Runtime stage
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=src

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmariadb3 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system lama \
    && useradd --system --gid lama --home-dir /app --no-create-home lama

COPY --from=build /install /usr/local

WORKDIR /app

# Note: the .env file is intentionally NOT copied into the image.
# Configuration is passed at runtime by docker compose (env_file).
COPY ./backend/ /app/

RUN chmod 755 ./entrypoint.sh \
    && mkdir -p /app/migrations \
    && chown -R lama:lama /app/migrations

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=5 \
    CMD curl --fail --silent http://localhost:5000/health || exit 1

# The entrypoint starts as root only to fix the ownership of the migrations volume,
# then drops privileges to the unprivileged `lama` user.
ENTRYPOINT ["./entrypoint.sh"]
