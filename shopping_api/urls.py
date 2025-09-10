"""
URL configuration for shopping_api app.
"""

from django.urls import path
from . import views

app_name = "shopping_api"

urlpatterns = [
    path("products/search/", views.ProductSearchView.as_view(), name="product_search"),
    path("health/", views.HealthView.as_view(), name="api_health"),
    path("stats/", views.StatsView.as_view(), name="api_stats"),
]
