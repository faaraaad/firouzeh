from django.contrib import admin
from .models import ShortenedURL


@admin.register(ShortenedURL)
class ShortenedURLAdmin(admin.ModelAdmin):
    list_display = ('short_code', 'original_url_truncated', 'clicks_count', 'created_at', 'last_accessed_at')
    search_fields = ('short_code', 'original_url')
    readonly_fields = ('created_at', 'last_accessed_at', 'url_hash', 'clicks_count')
    ordering = ('-created_at',)

    @admin.display(description='Original URL')
    def original_url_truncated(self, obj):
        return obj.original_url[:60] + ('...' if len(obj.original_url) > 60 else '')
