"""
Service layer for interacting with SerpAPI for Google Shopping data.
Implements async requests, caching, error handling, and rate limiting.
"""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import Product, ProductCache, SearchQuery, APIUsageStats

logger = logging.getLogger(__name__)


class SerpAPIError(Exception):
    """Custom exception for SerpAPI related errors."""

    pass


class SerpAPIClient:
    """
    Async client for SerpAPI Google Shopping requests with caching and optimization.
    """

    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.base_url = settings.SERPAPI_BASE_URL
        self.timeout = settings.SERPAPI_TIMEOUT
        self.cache_ttl = settings.CACHE_TTL

        # Create httpx client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={"User-Agent": "Smart-Shopper-Assistant/1.0"},
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _generate_query_hash(self, query: str) -> str:
        """Generate a hash for the query to use as cache key."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()

    def _extract_product_data(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and clean product data from SerpAPI response.
        """
        # Extract brand from title (basic heuristic)
        title = raw_result.get("title", "")
        brand = None

        # Look for common brand patterns in the title
        title_parts = title.split(" ")
        if title_parts:
            # First word is often the brand
            potential_brand = title_parts[0]
            if len(potential_brand) > 2:  # Avoid short words
                brand = potential_brand

        # Extract weight from extensions or title
        weight = None
        extensions = raw_result.get("extensions", [])
        for ext in extensions:
            if any(unit in ext.lower() for unit in ["oz", "lb", "kg", "g", "ml", "l"]):
                weight = ext
                break

        # If no weight in extensions, look in title
        if not weight:
            import re

            weight_match = re.search(
                r"(\d+(?:\.\d+)?)\s*(oz|lb|kg|g|ml|l)\b", title.lower()
            )
            if weight_match:
                weight = weight_match.group(0)

        return {
            "title": title,
            "product_id": raw_result.get("product_id", ""),
            "price": raw_result.get("price", ""),
            "extracted_price": raw_result.get("extracted_price"),
            "old_price": raw_result.get("old_price"),
            "extracted_old_price": raw_result.get("extracted_old_price"),
            "source": raw_result.get("source", ""),
            "source_icon": raw_result.get("source_icon"),
            "multiple_sources": raw_result.get("multiple_sources", False),
            "rating": raw_result.get("rating"),
            "reviews": raw_result.get("reviews"),
            "snippet": raw_result.get("snippet"),
            "thumbnail": raw_result.get("thumbnail"),
            "brand": brand,
            "weight": weight,
            "product_link": raw_result.get("product_link", ""),
            "additional_data": {
                "position": raw_result.get("position"),
                "badge": raw_result.get("badge"),
                "extensions": extensions,
                "second_hand_condition": raw_result.get("second_hand_condition"),
                "delivery": raw_result.get("delivery"),
            },
        }

    async def _check_cache(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Check if results are cached and not expired."""
        try:
            cache_entry = await sync_to_async(ProductCache.objects.get)(
                query_hash=query_hash
            )

            if not cache_entry.is_expired():
                # Increment hit count
                await sync_to_async(cache_entry.increment_hit_count)()

                logger.info(f"Cache hit for query hash: {query_hash}")
                return {
                    "results": cache_entry.results,
                    "count": cache_entry.results_count,
                    "cached": True,
                    "response_time_ms": cache_entry.response_time_ms,
                    "cache_hit": True,
                }
            else:
                # Cache expired, delete it
                await sync_to_async(cache_entry.delete)()
                logger.info(f"Expired cache entry deleted for query hash: {query_hash}")

        except ProductCache.DoesNotExist:
            pass

        return None

    async def _cache_results(
        self, query: str, query_hash: str, results: List[Dict], response_time_ms: int
    ) -> None:
        """Cache the search results."""
        try:
            expires_at = timezone.now() + timezone.timedelta(seconds=self.cache_ttl)

            await sync_to_async(ProductCache.objects.update_or_create)(
                query_hash=query_hash,
                defaults={
                    "query": query,
                    "results": results,
                    "results_count": len(results),
                    "response_time_ms": response_time_ms,
                    "expires_at": expires_at,
                    "hit_count": 0,
                },
            )
            logger.info(f"Cached {len(results)} results for query: {query}")

        except Exception as e:
            logger.error(f"Failed to cache results: {e}")

    async def _update_search_query_stats(
        self, query: str, query_hash: str, response_time_ms: int, results_count: int
    ) -> None:
        """Update search query statistics."""
        try:
            search_query, created = await sync_to_async(
                SearchQuery.objects.get_or_create
            )(
                query_hash=query_hash,
                defaults={
                    "query": query,
                    "response_time_ms": response_time_ms,
                    "results_count": results_count,
                },
            )

            if not created:
                search_query.search_count += 1
                search_query.response_time_ms = response_time_ms
                search_query.results_count = results_count
                await sync_to_async(search_query.save)(
                    update_fields=[
                        "search_count",
                        "response_time_ms",
                        "results_count",
                        "last_searched",
                    ]
                )

        except Exception as e:
            logger.error(f"Failed to update search query stats: {e}")

    async def _update_api_usage_stats(
        self,
        cached: bool,
        response_time_ms: int,
        results_count: int,
        error: bool = False,
    ) -> None:
        """Update daily API usage statistics."""
        try:
            today = timezone.now().date()

            stats, created = await sync_to_async(APIUsageStats.objects.get_or_create)(
                date=today,
                defaults={
                    "total_requests": 1,
                    "cached_requests": 1 if cached else 0,
                    "api_requests": 0 if cached else 1,
                    "avg_response_time_ms": response_time_ms,
                    "total_products_returned": results_count,
                    "error_count": 1 if error else 0,
                },
            )

            if not created:
                stats.total_requests += 1
                if cached:
                    stats.cached_requests += 1
                else:
                    stats.api_requests += 1

                # Update average response time
                total_time = (stats.avg_response_time_ms or 0) * (
                    stats.total_requests - 1
                ) + response_time_ms
                stats.avg_response_time_ms = int(total_time / stats.total_requests)

                stats.total_products_returned += results_count

                if error:
                    stats.error_count += 1

                await sync_to_async(stats.save)()

        except Exception as e:
            logger.error(f"Failed to update API usage stats: {e}")

    async def search_products(
        self, query: str, num_results: int = 40
    ) -> Dict[str, Any]:
        """
        Search for products using SerpAPI with caching and optimization.

        Args:
            query: Search query string
            num_results: Number of results to fetch (default: 40)

        Returns:
            Dictionary containing product results and metadata
        """
        start_time = time.time()
        query_hash = self._generate_query_hash(query)

        # Check cache first
        cached_result = await self._check_cache(query_hash)
        if cached_result:
            # Apply the requested limit to cached results
            if len(cached_result["results"]) > num_results:
                cached_result["results"] = cached_result["results"][:num_results]
                cached_result["count"] = len(cached_result["results"])

            await self._update_api_usage_stats(
                cached=True,
                response_time_ms=cached_result["response_time_ms"],
                results_count=cached_result["count"],
            )
            return cached_result

        # Make API request
        try:
            params = {
                "engine": "google_shopping",
                "q": query,
                "api_key": self.api_key,
                "num": min(num_results, 100),  # SerpAPI max is 100
                "gl": "us",  # Country
                "hl": "en",  # Language
            }

            logger.info(f"Making SerpAPI request for query: {query}")
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if "error" in data:
                raise SerpAPIError(f"SerpAPI error: {data['error']}")

            # Extract and process results
            raw_results = data.get("shopping_results", [])
            all_processed_results = []

            for raw_result in raw_results:
                try:
                    processed_result = self._extract_product_data(raw_result)
                    all_processed_results.append(processed_result)
                except Exception as e:
                    logger.warning(f"Failed to process result: {e}")
                    continue

            # Apply the requested limit to the results for the response
            limited_results = (
                all_processed_results[:num_results]
                if len(all_processed_results) > num_results
                else all_processed_results
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            # Cache the full processed results (not limited)
            await self._cache_results(
                query, query_hash, all_processed_results, response_time_ms
            )

            # Update statistics
            await self._update_search_query_stats(
                query, query_hash, response_time_ms, len(limited_results)
            )
            await self._update_api_usage_stats(
                cached=False,
                response_time_ms=response_time_ms,
                results_count=len(limited_results),
            )

            result = {
                "query": query,
                "results": limited_results,
                "count": len(limited_results),
                "cached": False,
                "response_time_ms": response_time_ms,
                "cache_hit": False,
            }

            logger.info(
                f"Successfully fetched {len(limited_results)} products for query: {query}"
            )
            return result

        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching products for query: {query}")
            await self._update_api_usage_stats(
                cached=False, response_time_ms=0, results_count=0, error=True
            )
            raise SerpAPIError("Request timeout")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while fetching products: {e}")
            await self._update_api_usage_stats(
                cached=False, response_time_ms=0, results_count=0, error=True
            )
            raise SerpAPIError(f"HTTP error: {e.response.status_code}")

        except Exception as e:
            logger.error(f"Unexpected error while fetching products: {e}")
            await self._update_api_usage_stats(
                cached=False, response_time_ms=0, results_count=0, error=True
            )
            raise SerpAPIError(f"Unexpected error: {str(e)}")


# Global client instance
_serp_client = None


async def get_serp_client() -> SerpAPIClient:
    """Get or create the global SerpAPI client instance."""
    global _serp_client
    if _serp_client is None:
        _serp_client = SerpAPIClient()
    return _serp_client


async def close_serp_client():
    """Close the global SerpAPI client."""
    global _serp_client
    if _serp_client:
        await _serp_client.close()
        _serp_client = None
