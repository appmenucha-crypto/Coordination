#!/bin/bash
set -e

echo "🔍 DATABASE_URL = $DATABASE_URL"

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🚀 Starting Gunicorn..."
exec gunicorn app.config.wsgi:application --bind 0.0.0.0:${PORT} --workers 3
