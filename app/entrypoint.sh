#!/bin/bash
set -e

# Appliquer les migrations Django
echo "🔄 Running Django migrations..."
python manage.py migrate --noinput

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Lancer Gunicorn
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
