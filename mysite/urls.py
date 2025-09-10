"""
URL configuration for mysite project.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


# Health check endpoint view
def health_check(request):
    """
    A simple health check endpoint that returns a 200 OK response.
    """
    return JsonResponse({"status": "healthy", "message": "Service is up and running"})


urlpatterns = [
    path("admin/", admin.site.urls),
    # Health check endpoint
    path("health/", health_check, name="health_check"),
    # API endpoints
    path("api/", include("shopping_api.urls")),
]
