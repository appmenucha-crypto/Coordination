#!/bin/bash
set -e

# Appliquer les migrations
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Lancer Gunicorn
exec "$@"
