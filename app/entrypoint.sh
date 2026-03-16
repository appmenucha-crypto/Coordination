# entrypoint.sh
#!/bin/bash
set -e

# Appliquer les migrations
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Lancer Gunicorn sur le port fourni par Dokploy
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 3
