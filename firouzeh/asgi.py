"""ASGI config for URL Shortener project."""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firouzeh.settings')
application = get_asgi_application()
