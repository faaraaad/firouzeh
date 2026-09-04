"""
Comprehensive test suite for the Django URL Shortener service.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from shortener.models import ShortenedURL
from shortener.utils import generate_short_code, BASE62_ALPHABET, MAX_CODE_LENGTH


class GenerateShortCodeTestCase(TestCase):
    """Test short code generation logic."""

    def test_code_length_and_characters(self):
        code = generate_short_code()
        self.assertEqual(len(code), MAX_CODE_LENGTH)
        for char in code:
            self.assertIn(char, BASE62_ALPHABET)

    def test_custom_length(self):
        code = generate_short_code(length=8)
        self.assertEqual(len(code), 8)



class URLShortenerAPITestCase(TestCase):
    """Integration tests for the URL shortener API and redirection."""

    def setUp(self):
        self.client = Client()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_shorten_valid_url_success(self):
        """Test shortening a valid URL returns 201 with a <= 5 char code."""
        target_url = "https://www.example.com/some/deep/page?query=param#fragment"
        response = self.client.post(
            reverse('shortener:api-shorten'),
            data=json.dumps({"url": target_url}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['is_new'])
        self.assertIn('short_code', data)
        self.assertLessEqual(len(data['short_code']), MAX_CODE_LENGTH)
        self.assertEqual(len(data['short_code']), 5)
        self.assertEqual(data['original_url'], target_url)

        # Verify persisted in database
        db_obj = ShortenedURL.objects.get(short_code=data['short_code'])
        self.assertEqual(db_obj.original_url, target_url)

    def test_redirect_to_original_url(self):
        """Test accessing the short code redirects (302) to the original URL."""
        original_url = "https://github.com/django/django"
        obj, _ = ShortenedURL.create_or_get(original_url)

        response = self.client.get(f"/{obj.short_code}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], original_url)

        # Verify clicks count updated
        obj.refresh_from_db()
        self.assertEqual(obj.clicks_count, 1)
        self.assertIsNotNone(obj.last_accessed_at)

    def test_short_code_length_strictly_enforced(self):
        """Test multiple varying URLs strictly adhere to maximum 5-char limit."""
        urls = [
            f"https://example{i}.org/resource/path/{i}?q={i * 100}"
            for i in range(25)
        ]
        for url in urls:
            obj, _ = ShortenedURL.create_or_get(url)
            self.assertLessEqual(
                len(obj.short_code),
                5,
                f"Short code '{obj.short_code}' exceeds 5 characters for URL {url}"
            )

    def test_idempotent_deduplication(self):
        """Test that submitting the same URL multiple times reuses the existing code."""
        url = "https://docs.python.org/3/library/hashlib.html"
        res1 = self.client.post(
            reverse('shortener:api-shorten'),
            data=json.dumps({"url": url}),
            content_type="application/json"
        )
        self.assertEqual(res1.status_code, 201)
        code1 = res1.json()['short_code']

        # Second request for same URL
        res2 = self.client.post(
            reverse('shortener:api-shorten'),
            data=json.dumps({"url": url}),
            content_type="application/json"
        )
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertFalse(data2['is_new'])
        self.assertEqual(data2['short_code'], code1)

        # Ensure only 1 record created in database
        self.assertEqual(ShortenedURL.objects.filter(original_url=url).count(), 1)

    def test_invalid_url_rejection(self):
        """Test invalid URLs return 400 Bad Request."""
        invalid_urls = [
            "",
            "not-a-valid-url",
            "ftp://files.example.com",
            "http://",
            "   ",
        ]
        for invalid_url in invalid_urls:
            response = self.client.post(
                reverse('shortener:api-shorten'),
                data=json.dumps({"url": invalid_url}),
                content_type="application/json"
            )
            self.assertEqual(
                response.status_code,
                400,
                f"Expected 400 for '{invalid_url}', got {response.status_code}"
            )
            self.assertEqual(response.json()['status'], 'error')

    def test_non_existent_short_code_returns_404(self):
        """Test requesting an unknown short code returns 404."""
        response = self.client.get("/nonEx")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')

    def test_stats_api_endpoint(self):
        """Test the stats endpoint returns click metrics."""
        url = "https://news.ycombinator.com"
        obj, _ = ShortenedURL.create_or_get(url)

        # Simulate 3 clicks
        self.client.get(f"/{obj.short_code}")
        self.client.get(f"/{obj.short_code}")
        self.client.get(f"/{obj.short_code}")

        res = self.client.get(reverse('shortener:api-stats', kwargs={'short_code': obj.short_code}))
        self.assertEqual(res.status_code, 200)
        stats = res.json()
        self.assertEqual(stats['status'], 'success')
        self.assertEqual(stats['clicks_count'], 3)
        self.assertEqual(stats['original_url'], url)

    def test_caching_behavior(self):
        """Test that get_by_code serves directly from cache on repeated calls."""
        url = "https://speedtest.net"
        obj, _ = ShortenedURL.create_or_get(url)

        # Cache key exists
        cache_key = ShortenedURL.get_cache_key(obj.short_code)
        self.assertEqual(cache.get(cache_key), url)

        # Retrieve via get_by_code
        cached_result = ShortenedURL.get_by_code(obj.short_code)
        self.assertEqual(cached_result, url)


from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from shortener.serializers import (
    ShortenURLRequestSerializer,
    ShortenedURLSerializer,
    URLStatsResponseSerializer,
)


class DjangoRestFrameworkTestCase(APITestCase):
    """Specific test suite validating DRF integration, serializers, and clients."""

    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_drf_apiclient_json_payload(self):
        """Test DRF APIClient creates shortened URL with JSON payload."""
        url = "https://www.djangoproject.com/community/"
        response = self.client.post(
            reverse('shortener:api-shorten'),
            data={'url': url},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['original_url'], url)
        self.assertIn('short_code', response.data)
        self.assertIn('short_url', response.data)

    def test_drf_apiclient_form_payload(self):
        """Test DRF APIClient handles standard multipart/form-data payload."""
        url = "https://www.django-rest-framework.org"
        response = self.client.post(
            reverse('shortener:api-shorten'),
            data={'url': url},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['original_url'], url)

    def test_drf_serializer_validation(self):
        """Test ShortenURLRequestSerializer validation behavior."""
        # Valid URL
        s_valid = ShortenURLRequestSerializer(data={'url': 'python.org'})
        self.assertTrue(s_valid.is_valid())
        self.assertEqual(s_valid.validated_data['url'], 'https://python.org')

        # Empty URL
        s_empty = ShortenURLRequestSerializer(data={'url': ''})
        self.assertFalse(s_empty.is_valid())
        self.assertIn('url', s_empty.errors)

        # Missing URL
        s_missing = ShortenURLRequestSerializer(data={})
        self.assertFalse(s_missing.is_valid())
        self.assertIn('url', s_missing.errors)

    def test_drf_stats_serializer_and_404(self):
        """Test DRF stats retrieval and 404 response on missing short code."""
        # Missing short code
        response = self.client.get(
            reverse('shortener:api-stats', kwargs={'short_code': 'nonEx'})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['status'], 'error')

        # Existing short code
        obj, _ = ShortenedURL.create_or_get('https://example.com/drf-stats')
        response = self.client.get(
            reverse('shortener:api-stats', kwargs={'short_code': obj.short_code})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['short_code'], obj.short_code)
        self.assertEqual(response.data['status'], 'success')

    def test_drf_browsable_api_rendering(self):
        """Test that DRF's BrowsableAPIRenderer responds to text/html requests."""
        response = self.client.get(
            reverse('shortener:api-shorten'),
            HTTP_ACCEPT='text/html'
        )
        # GET on ShortenAPIView is 405 Method Not Allowed, but renders via DRF Browsable API HTML
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertIn('text/html', response['Content-Type'])

    def test_dynamic_base_url_resolution(self):
        """Test that get_service_base_url uses incoming request origin when accessing from external host."""
        from shortener.utils import get_service_base_url
        from django.test import RequestFactory

        rf = RequestFactory()
        req = rf.get('/', HTTP_HOST='188.121.124.135:9000')

        # When settings.BASE_URL is localhost, but request is from server IP, prefer request host
        with self.settings(BASE_URL='http://localhost:9000'):
            self.assertEqual(get_service_base_url(req), 'http://188.121.124.135:9000')

        # When settings.BASE_URL is empty, prefer request host
        with self.settings(BASE_URL=''):
            self.assertEqual(get_service_base_url(req), 'http://188.121.124.135:9000')


