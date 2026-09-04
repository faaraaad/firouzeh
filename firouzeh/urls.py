"""
Root URL Configuration for URL Shortener Service.
"""
from django.contrib import admin
from django.urls import path, include
from shortener.views import HomeView, RedirectURLView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('', include('shortener.urls')),
    # Redirect route for short codes (must be at root level)
    path('<str:short_code>', RedirectURLView.as_view(), name='redirect-url'),
    path('<str:short_code>/', RedirectURLView.as_view(), name='redirect-url-slash'),
]
