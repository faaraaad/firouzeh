"""
Data models for the URL Shortener service.
"""
from django.db import models, transaction, IntegrityError
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from .utils import (
    compute_url_hash,
    generate_short_code,
)

MAX_CODE_LENGTH = getattr(settings, 'SHORT_CODE_MAX_LENGTH', 5)


class ShortenedURL(models.Model):
    """
    Represents a shortened URL mapping.
    Indexed on short_code (primary lookup) and url_hash (deduplication lookup).
    """
    original_url = models.URLField(
        max_length=2048,
        help_text="The original long destination URL"
    )
    short_code = models.CharField(
        max_length=MAX_CODE_LENGTH,
        unique=True,
        db_index=True,
        help_text=f"Unique short code of at most {MAX_CODE_LENGTH} characters"
    )
    url_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash of original_url for fast deduplication lookup"
    )
    clicks_count = models.PositiveBigIntegerField(
        default=0,
        help_text="Total number of times this short link has been accessed"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the short URL was created"
    )
    last_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent access/redirection"
    )

    class Meta:
        verbose_name = "Shortened URL"
        verbose_name_plural = "Shortened URLs"
        indexes = [
            models.Index(fields=['short_code'], name='idx_short_code'),
            models.Index(fields=['url_hash'], name='idx_url_hash'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.short_code} -> {self.original_url[:50]}"

    @classmethod
    def get_cache_key(cls, short_code: str) -> str:
        """Standardized cache key for a short code."""
        return f"short_url:{short_code}"

    @classmethod
    def get_by_code(cls, short_code: str):
        """
        Fast lookup with caching:
        1. Check memory cache.
        2. Fallback to database if cache miss.
        3. Populate cache on hit.
        """
        cache_key = cls.get_cache_key(short_code)
        cached_url = cache.get(cache_key)
        if cached_url is not None:
            return cached_url

        try:
            record = cls.objects.only('original_url').get(short_code=short_code)
            ttl = getattr(settings, 'SHORT_URL_CACHE_TTL', 86400)
            cache.set(cache_key, record.original_url, timeout=ttl)
            return record.original_url
        except cls.DoesNotExist:
            return None

    @classmethod
    def create_or_get(cls, original_url: str) -> tuple['ShortenedURL', bool]:
        """
        Idempotent creation or retrieval of a shortened URL.
        - Returns (instance, created_bool)
        - Strictly guarantees short_code length <= 5.
        - Resolves collisions deterministically.
        """
        url_hash = compute_url_hash(original_url)

        # Check if URL was already shortened
        existing = cls.objects.filter(url_hash=url_hash, original_url=original_url).first()
        if existing:
            # Refresh cache
            cache.set(cls.get_cache_key(existing.short_code), existing.original_url, timeout=settings.SHORT_URL_CACHE_TTL)
            return existing, False

        # Generate unique code with retry on collision
        max_attempts = 100
        for _ in range(max_attempts):
            candidate_code = generate_short_code(length=MAX_CODE_LENGTH)
            
            try:
                with transaction.atomic():
                    instance = cls.objects.create(
                        original_url=original_url,
                        short_code=candidate_code,
                        url_hash=url_hash,
                    )
                    cache.set(
                        cls.get_cache_key(candidate_code),
                        original_url,
                        timeout=settings.SHORT_URL_CACHE_TTL
                    )
                    return instance, True
            except IntegrityError:
                # Collision detected, retry or check if another worker created same url
                existing = cls.objects.filter(url_hash=url_hash, original_url=original_url).first()
                if existing:
                    return existing, False
                continue

        raise RuntimeError("Failed to generate a unique short code within maximum attempt limit.")

    @classmethod
    def record_access(cls, short_code: str) -> None:
        """
        Atomically record an access event by short_code.
        Issues a single UPDATE — no prior SELECT/object needed.
        """
        cls.objects.filter(short_code=short_code).update(
            clicks_count=models.F('clicks_count') + 1,
            last_accessed_at=timezone.now()
        )
