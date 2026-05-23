#!/usr/bin/env bash
set -euo pipefail

# Wait for PostgreSQL only when host/port are explicitly provided.
if [[ -n "${POSTGRES_HOST:-}" && -n "${POSTGRES_PORT:-}" ]]; then
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn IGI_LR5.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
