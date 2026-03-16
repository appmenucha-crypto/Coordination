#!/bin/bash
set -e

# ------------------------------------------------------------
# Affichage DATABASE_URL
# ------------------------------------------------------------
echo "🔍 DATABASE_URL = $DATABASE_URL"

# ------------------------------------------------------------
# Appliquer les migrations
# ------------------------------------------------------------
echo "🔄 Running migrations..."
python manage.py migrate --noinput

# ------------------------------------------------------------
# Créer l’utilisateur superadmin si inexistant
# ------------------------------------------------------------
echo "👤 Creating superuser if not exists..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="admin123"
    )
END

# ------------------------------------------------------------
# Collecter les fichiers statiques
# ------------------------------------------------------------
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# ------------------------------------------------------------
# Lancer Gunicorn
# ------------------------------------------------------------
echo "🚀 Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
