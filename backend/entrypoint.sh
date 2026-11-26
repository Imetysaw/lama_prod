#!/usr/bin/env bash
set -euo pipefail

# Run commands as the unprivileged `lama` user. When started as root, first make sure
# that user can write to the migrations volume (volumes created by older versions of
# LaMa are owned by root).
RUN_AS=()
if [ "$(id -u)" = "0" ]; then
    chown -R lama:lama /app/migrations
    RUN_AS=(setpriv --reuid=lama --regid=lama --init-groups)
fi

# Refuse to start in production with the placeholder values from .env.prod.example
if [ "${APP_ENV:-production}" = "production" ]; then
    for var in SECRET_KEY DB_PASSWORD SUPER_PASSWORD; do
        if [ "${!var:-}" = "CHANGE_ME" ]; then
            echo "ERROR: $var is still set to CHANGE_ME in .env.prod" >&2
            exit 1
        fi
    done
fi

# All gunicorn workers must sign login tokens with the same key. If no SECRET_KEY is
# configured, generate one for this container run (users are logged out on restart).
if [ -z "${SECRET_KEY:-}" ]; then
    echo "WARNING: SECRET_KEY is not set, generating a temporary one." >&2
    SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
    export SECRET_KEY
fi

# Database migrations and super admin creation
"${RUN_AS[@]}" flask db-safe init
"${RUN_AS[@]}" flask db migrate
"${RUN_AS[@]}" flask db upgrade
"${RUN_AS[@]}" flask db-safe add-super-admin

if [ "${APP_ENV:-production}" = "development" ]; then
    echo "Starting Flask development server (APP_ENV=development)"
    exec "${RUN_AS[@]}" flask run --host=0.0.0.0 --port="${FLASK_RUN_PORT:-5000}" --debug
fi

echo "Starting gunicorn (APP_ENV=${APP_ENV:-production})"
exec "${RUN_AS[@]}" gunicorn \
    --bind "0.0.0.0:${FLASK_RUN_PORT:-5000}" \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile - \
    "src:create_app()"
