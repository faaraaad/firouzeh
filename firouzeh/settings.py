"""
Django settings for URL Shortener project.
"""
from pathlib import Path
import os
import string

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

_secret_key = os.environ.get('DJANGO_SECRET_KEY', '')
if not _secret_key:
    if not DEBUG:
        raise ValueError(
            "DJANGO_SECRET_KEY environment variable must be set in production. "
            "Generate one with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
        )
    _secret_key = 'django-insecure-dev-only-key-do-not-use-in-production'
SECRET_KEY = _secret_key

_allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(',') if host.strip()]

# Automatically ensure deployment host and base URL are permitted
if '*' not in ALLOWED_HOSTS:
    for default_host in ['188.121.124.135', 'localhost', '127.0.0.1']:
        if default_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(default_host)
    _base_url_env = os.environ.get('SHORTENER_BASE_URL', '')
    if _base_url_env:
        from urllib.parse import urlparse
        _parsed_host = urlparse(_base_url_env).hostname
        if _parsed_host and _parsed_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_parsed_host)

_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins.split(',') if origin.strip()]
elif os.environ.get('SHORTENER_BASE_URL', ''):
    CSRF_TRUSTED_ORIGINS = [os.environ.get('SHORTENER_BASE_URL', '').rstrip('/')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party Apps
    'rest_framework',
    # Shortener App
    'shortener.apps.ShortenerConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'firouzeh.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'firouzeh.wsgi.application'
ASGI_APPLICATION = 'firouzeh.asgi.application'

# Database configuration
_sqlite_data_dir = os.environ.get('SQLITE_DATA_DIR', '')
if _sqlite_data_dir:
    _db_path = Path(_sqlite_data_dir) / 'db.sqlite3'
    _db_path.parent.mkdir(parents=True, exist_ok=True)
else:
    _db_path = BASE_DIR / 'db.sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _db_path,
    }
}

# High-Performance Caching Layer
# Uses Redis when REDIS_URL is set (production/Docker), falls back to LocMem for local dev.
REDIS_URL = os.environ.get('REDIS_URL', '')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 86400,  # 24 hours
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'MAX_ENTRIES': 100000,
                # Silently fall back to a cache miss instead of crashing if Redis
                # becomes temporarily unavailable — redirection still works via DB.
                'IGNORE_EXCEPTIONS': True,
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'url-shortener-cache',
            'TIMEOUT': 86400,  # 24 hours
            'OPTIONS': {
                'MAX_ENTRIES': 100000
            }
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# URL Shortener Configuration
SHORT_CODE_MAX_LENGTH = 5
SHORT_CODE_CHARACTERS = string.digits + string.ascii_letters
SHORT_URL_REDIRECT_STATUS = 302  # 302 Found allows accurate analytics and click tracking
SHORT_URL_CACHE_TTL = 86400  # 24 hours
BASE_URL = os.environ.get('SHORTENER_BASE_URL', '')

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}
