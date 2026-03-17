"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 1. Obtenir l'application Django de base
application = get_wsgi_application()

# 2. Importer WhiteNoise
from whitenoise import WhiteNoise

# 3. Envelopper l'application avec WhiteNoise pour les fichiers statiques (pratique standard)
application = WhiteNoise(application)

# 4. Ajouter le répertoire des médias pour que WhiteNoise puisse aussi les servir
# Note : Assurez-vous que votre MEDIA_ROOT dans settings.py correspond à '/app/media'
application.add_files('/app/media', prefix='media/')
