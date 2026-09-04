"""URL configuration for shortener app."""
from django.urls import path
from .views import ShortenAPIView, URLStatsAPIView

app_name = 'shortener'

urlpatterns = [
    path('api/shorten/', ShortenAPIView.as_view(), name='api-shorten'),
    path('api/urls/<str:short_code>/stats/', URLStatsAPIView.as_view(), name='api-stats'),
]
