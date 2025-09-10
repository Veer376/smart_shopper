"""
Views for the Smart Shopping Assistant API.
"""

import asyncio
import logging
from typing import Dict, Any

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from asgiref.sync import async_to_sync

from .services import get_serp_client, SerpAPIError

logger = logging.getLogger(__name__)


class ProductSearchView(APIView):
    """
    API View to search for products using the Smart Shopping Assistant.

    Endpoint: GET /api/products/search/?q=<query>&limit=<number>

    Query Parameters:
    - q (required): Product search query
    - limit (optional): Number of results to return (default: 20, max: 100)
    """

    def get(self, request):
        """Handle GET requests for product search."""
        # Validate query parameter
        query = request.GET.get("q", "").strip()
        if not query:
            return Response(
                {
                    "error": 'Query parameter "q" is required',
                    "message": "Please provide a product name to search for",
                    "example": "/api/products/search/?q=365+WholeFoods+Peanut+Butter",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate and parse limit parameter
        try:
            limit = int(request.GET.get("limit", 20))
            if limit < 1:
                limit = 20
            elif limit > 100:
                limit = 100
        except ValueError:
            limit = 20

        try:
            # Use async_to_sync to call the async service
            result = async_to_sync(self._search_products)(query, limit)
            return Response(result)

        except SerpAPIError as e:
            logger.error(f"SerpAPI error for query '{query}': {e}")
            return Response(
                {
                    "error": "Search service temporarily unavailable",
                    "message": str(e),
                    "query": query,
                    "results": [],
                    "count": 0,
                    "cached": False,
                    "response_time_ms": 0,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as e:
            logger.error(f"Unexpected error for query '{query}': {e}")
            return Response(
                {
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while processing your request",
                    "query": query,
                    "results": [],
                    "count": 0,
                    "cached": False,
                    "response_time_ms": 0,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    async def _search_products(self, query: str, limit: int) -> Dict[str, Any]:
        """
        Async helper method to search for products.
        """
        client = await get_serp_client()
        result = await client.search_products(query, num_results=limit)

        # Add metadata for API response
        result.update(
            {
                "api_version": "1.0.0",
                "service": "Smart Shopping Assistant",
                "query_processed": query,
                "limit": limit,
            }
        )

        return result


class HealthView(APIView):
    """
    Health check endpoint for the shopping API.

    Endpoint: GET /api/health/
    """

    def get(self, request):
        """Return API health status with system information."""
        try:
            # Test database connectivity
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = "unhealthy"

        # Test cache connectivity
        try:
            from django.core.cache import cache

            cache.set("health_check", "test", 10)
            cache_value = cache.get("health_check")
            cache_status = "healthy" if cache_value == "test" else "unhealthy"
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            cache_status = "unhealthy"

        # Overall health status
        overall_status = (
            "healthy"
            if db_status == "healthy" and cache_status == "healthy"
            else "degraded"
        )

        response_data = {
            "status": overall_status,
            "service": "Smart Shopping Assistant API",
            "version": "1.0.0",
            "components": {
                "database": db_status,
                "cache": cache_status,
                "api": "healthy",
            },
            "endpoints": {
                "product_search": "/api/products/search/?q=<query>",
                "health": "/api/health/",
            },
        }

        # Return appropriate status code
        if overall_status == "healthy":
            return Response(response_data)
        else:
            return Response(response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class StatsView(APIView):
    """
    API statistics and analytics endpoint.

    Endpoint: GET /api/stats/
    """

    def get(self, request):
        """Return API usage statistics."""
        try:
            from .models import APIUsageStats, SearchQuery, ProductCache
            from django.utils import timezone
            from django.db.models import Sum, Avg, Count

            # Get today's stats
            today = timezone.now().date()
            today_stats = APIUsageStats.objects.filter(date=today).first()

            # Get top search queries
            top_queries = SearchQuery.objects.order_by("-search_count")[:10]

            # Get cache statistics
            cache_stats = ProductCache.objects.aggregate(
                total_entries=Count("id"),
                total_hits=Sum("hit_count"),
                avg_response_time=Avg("response_time_ms"),
            )

            # Calculate total statistics
            total_stats = APIUsageStats.objects.aggregate(
                total_requests=Sum("total_requests"),
                total_cached=Sum("cached_requests"),
                total_api_calls=Sum("api_requests"),
                total_errors=Sum("error_count"),
            )

            response_data = {
                "today": {
                    "total_requests": today_stats.total_requests if today_stats else 0,
                    "cached_requests": (
                        today_stats.cached_requests if today_stats else 0
                    ),
                    "api_requests": today_stats.api_requests if today_stats else 0,
                    "cache_hit_rate": today_stats.cache_hit_rate if today_stats else 0,
                    "avg_response_time_ms": (
                        today_stats.avg_response_time_ms if today_stats else 0
                    ),
                    "error_count": today_stats.error_count if today_stats else 0,
                },
                "total": {
                    "requests": total_stats["total_requests"] or 0,
                    "cached_requests": total_stats["total_cached"] or 0,
                    "api_calls": total_stats["total_api_calls"] or 0,
                    "errors": total_stats["total_errors"] or 0,
                    "cache_hit_rate": (
                        (total_stats["total_cached"] or 0)
                        / max(total_stats["total_requests"] or 1, 1)
                        * 100
                    ),
                },
                "cache": {
                    "total_entries": cache_stats["total_entries"] or 0,
                    "total_hits": cache_stats["total_hits"] or 0,
                    "avg_response_time_ms": int(cache_stats["avg_response_time"] or 0),
                },
                "top_queries": [
                    {
                        "query": q.query,
                        "search_count": q.search_count,
                        "last_searched": (
                            q.last_searched.isoformat() if q.last_searched else None
                        ),
                    }
                    for q in top_queries
                ],
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return Response(
                {"error": "Failed to fetch statistics", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
