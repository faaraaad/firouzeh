"""
Serializers for the URL Shortener REST API.
"""
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import ShortenedURL
from .utils import normalize_and_validate_url


class ShortenURLRequestSerializer(serializers.Serializer):
    """
    Validates payload for creating or retrieving a shortened URL.
    Expected payload: {"url": "https://example.com/..."}
    """
    url = serializers.CharField(
        max_length=2048,
        required=True,
        allow_blank=False,
        error_messages={
            'required': "Missing 'url' parameter in request.",
            'blank': "URL must be a non-empty string."
        }
    )

    def validate_url(self, value):
        trimmed = value.strip() if isinstance(value, str) else ''
        if not trimmed:
            raise serializers.ValidationError("URL must be a non-empty string.")
        try:
            return normalize_and_validate_url(trimmed)
        except DjangoValidationError as exc:
            msg = exc.message if hasattr(exc, 'message') else str(exc)
            raise serializers.ValidationError(msg)


class ShortenedURLSerializer(serializers.ModelSerializer):
    """
    ModelSerializer for ShortenedURL instances.
    """
    short_url = serializers.SerializerMethodField()

    class Meta:
        model = ShortenedURL
        fields = [
            'short_code',
            'short_url',
            'original_url',
            'clicks_count',
            'created_at',
            'last_accessed_at',
        ]
        read_only_fields = fields

    def get_short_url(self, obj) -> str:
        request = self.context.get('request')
        base_url = getattr(settings, 'BASE_URL', '')
        if not base_url and request:
            base_url = request.build_absolute_uri('/')[:-1]
        return f"{base_url}/{obj.short_code}"


class URLStatsResponseSerializer(serializers.ModelSerializer):
    """
    Serializer representing stats output for a shortened URL.
    """
    status = serializers.SerializerMethodField()
    short_url = serializers.SerializerMethodField()

    class Meta:
        model = ShortenedURL
        fields = [
            'status',
            'short_code',
            'short_url',
            'original_url',
            'clicks_count',
            'created_at',
            'last_accessed_at',
        ]
        read_only_fields = fields

    def get_status(self, obj) -> str:
        return 'success'

    def get_short_url(self, obj) -> str:
        request = self.context.get('request')
        base_url = getattr(settings, 'BASE_URL', '')
        if not base_url and request:
            base_url = request.build_absolute_uri('/')[:-1]
        return f"{base_url}/{obj.short_code}"
