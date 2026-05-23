#!/usr/bin/env bash
set -euo pipefail

if [[ "${DB_ENGINE:-}" == "postgres" || "${DB_ENGINE:-}" == "postgresql" ]]; then
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput  # добавляем сбор статики

# Запускаем Gunicorn
gunicorn IGI_LR5.wsgi:application --bind 0.0.0.0:8000 --workers 3
