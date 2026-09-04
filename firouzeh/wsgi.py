"""WSGI config for URL Shortener project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firouzeh.settings')
application = get_wsgi_application()
