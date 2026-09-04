"""
Utility functions for URL validation, hashing, and code generation.
"""
import hashlib
import secrets
import string
from urllib.parse import urlparse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

BASE62_ALPHABET = getattr(
    settings,
    'SHORT_CODE_CHARACTERS',
    string.digits + string.ascii_letters
)
MAX_CODE_LENGTH = getattr(settings, 'SHORT_CODE_MAX_LENGTH', 5)


def compute_url_hash(url: str) -> str:
    """Compute SHA-256 hash of a normalized URL for fast indexed lookups."""
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def normalize_and_validate_url(raw_url: str) -> str:
    """
    Validate and normalize long URL.
    - Trims whitespace
    - Ensures valid http/https scheme
    - Validates URL syntax
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValidationError("URL must be a non-empty string.")

    url = raw_url.strip()

    # If scheme missing, default to https://
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Validate using Django's URLValidator
    validator = URLValidator(schemes=['http', 'https'])
    try:
        validator(url)
    except ValidationError:
        raise ValidationError("Invalid URL format. Please provide a valid HTTP or HTTPS URL.")

    # Parse URL components
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValidationError("URL must contain a valid domain name.")

    return url


def generate_short_code(length: int = MAX_CODE_LENGTH) -> str:
    """
    Generate a secure, random Base62 short code of specified `length` characters (default 5).
    """
    return ''.join(secrets.choice(BASE62_ALPHABET) for _ in range(length))


def get_service_base_url(request=None) -> str:
    """
    Resolve the base URL for building short URLs.
    - If request is provided, automatically prefer the client's actual host/origin
      if settings.BASE_URL is unset, or if settings.BASE_URL is 'localhost'/'127.0.0.1'
      while client is accessing from an external IP/domain (e.g. cloud server).
    - Otherwise fall back to settings.BASE_URL or request origin.
    """
    base_url = getattr(settings, 'BASE_URL', '').strip().rstrip('/')
    if request:
        current_origin = request.build_absolute_uri('/')[:-1]
        if not base_url:
            return current_origin
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            req_host = request.get_host()
            if req_host and 'localhost' not in req_host and '127.0.0.1' not in req_host:
                return current_origin
        return base_url
    return base_url

