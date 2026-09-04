"""
Views and API handlers for the URL Shortener service using Django REST Framework.
"""
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.views import View
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ShortenedURL
from .serializers import (
    ShortenURLRequestSerializer,
    URLStatsResponseSerializer,
)
from .utils import MAX_CODE_LENGTH


class ShortenAPIView(APIView):
    """
    API endpoint to shorten a long URL.
    Method: POST
    Payload: {"url": "https://example.com/long/path"}
    """
    def post(self, request, *args, **kwargs):
        # Support both JSON body and form-encoded data natively via DRF request.data
        data = request.data if isinstance(request.data, dict) else {}
        if not data or 'url' not in data:
            return Response({
                'status': 'error',
                'message': "Missing 'url' parameter in request."
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = ShortenURLRequestSerializer(data=data)
        if not serializer.is_valid():
            errors = serializer.errors.get('url', [])
            msg = errors[0] if errors else 'Invalid request data.'
            return Response({
                'status': 'error',
                'message': str(msg),
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_url = serializer.validated_data['url']

        # Create or retrieve shortened URL
        try:
            short_obj, is_created = ShortenedURL.create_or_get(validated_url)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error while generating short URL: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Build full short URL
        base_url = getattr(settings, 'BASE_URL', '') or request.build_absolute_uri('/')[:-1]
        full_short_url = f"{base_url}/{short_obj.short_code}"

        response_payload = {
            'status': 'success',
            'short_code': short_obj.short_code,
            'short_url': full_short_url,
            'original_url': short_obj.original_url,
            'is_new': is_created,
            'created_at': short_obj.created_at.isoformat()
        }

        return Response(
            response_payload,
            status=status.HTTP_201_CREATED if is_created else status.HTTP_200_OK
        )


class RedirectURLView(View):
    """
    Redirects a shortened code to the original destination URL.
    Method: GET /<short_code>
    """
    def get(self, request, short_code, *args, **kwargs):
        if not short_code or len(short_code) > MAX_CODE_LENGTH:
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid short code. Must be <= {MAX_CODE_LENGTH} characters.'
            }, status=404)

        original_url = ShortenedURL.get_by_code(short_code)
        if not original_url:
            return JsonResponse({
                'status': 'error',
                'message': 'Short URL not found or has expired.'
            }, status=404)

        # Record analytics atomically — single UPDATE, no prior SELECT needed.
        try:
            ShortenedURL.record_access(short_code)
        except Exception:
            pass  # Do not block redirection on analytics update failures

        status_code = getattr(settings, 'SHORT_URL_REDIRECT_STATUS', 302)
        return HttpResponseRedirect(original_url, status=status_code)


class URLStatsAPIView(APIView):
    """
    API endpoint to retrieve statistics for a shortened URL.
    Method: GET /api/urls/<short_code>/stats/
    """
    def get(self, request, short_code, *args, **kwargs):
        obj = ShortenedURL.objects.filter(short_code=short_code).first()
        if not obj:
            return Response({
                'status': 'error',
                'message': 'Short code not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = URLStatsResponseSerializer(obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class HomeView(TemplateView):
    """
    Interactive web interface for creating and testing short URLs.
    """
    template_name = 'shortener/index.html'

