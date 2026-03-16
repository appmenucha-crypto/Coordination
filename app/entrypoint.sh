#!/bin/bash
set -e

echo "🔍 DATABASE_URL = postgresql://esther:123456@coodination-des-dpartements-departements-a4fmbm:5432/departements"

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🚀 Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
