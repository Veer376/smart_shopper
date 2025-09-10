"""
Django models for the Smart Shopping Assistant.
"""

from django.db import models
from django.utils import timezone
import json


class Product(models.Model):
    """
    Model to store product information from Google Shopping API.
    """

    # Core product information
    title = models.CharField(max_length=500)
    product_id = models.CharField(max_length=100, unique=True, db_index=True)

    # Price information
    price = models.CharField(max_length=50, blank=True, null=True)
    extracted_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    old_price = models.CharField(max_length=50, blank=True, null=True)
    extracted_old_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # Source and reliability information
    source = models.CharField(max_length=200)
    source_icon = models.URLField(blank=True, null=True)
    multiple_sources = models.BooleanField(default=False)

    # Product ratings and reviews
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    reviews = models.IntegerField(blank=True, null=True)
    snippet = models.TextField(blank=True, null=True)

    # Product images
    thumbnail = models.URLField(blank=True, null=True)

    # Product details
    brand = models.CharField(max_length=200, blank=True, null=True)
    weight = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=200, blank=True, null=True)

    # Links
    product_link = models.URLField()

    # Additional data (JSON field for extensibility)
    additional_data = models.JSONField(default=dict, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["source"]),
            models.Index(fields=["rating"]),
            models.Index(fields=["extracted_price"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.source} - {self.price}"


class SearchQuery(models.Model):
    """
    Model to track search queries for analytics and optimization.
    """

    query = models.CharField(max_length=500, db_index=True)
    query_hash = models.CharField(
        max_length=64, unique=True, db_index=True
    )  # For fast lookups
    search_count = models.IntegerField(default=1)
    last_searched = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Response metadata
    response_time_ms = models.IntegerField(blank=True, null=True)
    results_count = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = "search_queries"
        ordering = ["-last_searched"]
        indexes = [
            models.Index(fields=["query_hash"]),
            models.Index(fields=["search_count"]),
            models.Index(fields=["last_searched"]),
        ]

    def __str__(self):
        return f"{self.query} (searched {self.search_count} times)"


class ProductCache(models.Model):
    """
    Model to cache search results for faster responses.
    """

    query_hash = models.CharField(max_length=64, unique=True, db_index=True)
    query = models.CharField(max_length=500)

    # Cached response data
    results = models.JSONField()  # Stores the full product results
    results_count = models.IntegerField()

    # Cache metadata
    response_time_ms = models.IntegerField()
    cached_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    hit_count = models.IntegerField(default=0)

    class Meta:
        db_table = "product_cache"
        ordering = ["-cached_at"]
        indexes = [
            models.Index(fields=["query_hash"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["hit_count"]),
        ]

    def __str__(self):
        return f"Cache for '{self.query}' ({self.results_count} results)"

    def is_expired(self):
        """Check if the cache entry is expired."""
        return timezone.now() > self.expires_at

    def increment_hit_count(self):
        """Increment the cache hit count."""
        self.hit_count += 1
        self.save(update_fields=["hit_count"])


class APIUsageStats(models.Model):
    """
    Model to track API usage statistics for monitoring and optimization.
    """

    date = models.DateField(unique=True, db_index=True)

    # Request counts
    total_requests = models.IntegerField(default=0)
    cached_requests = models.IntegerField(default=0)
    api_requests = models.IntegerField(default=0)  # Actual SerpAPI calls

    # Performance metrics
    avg_response_time_ms = models.IntegerField(blank=True, null=True)
    total_products_returned = models.IntegerField(default=0)

    # Error tracking
    error_count = models.IntegerField(default=0)
    timeout_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "api_usage_stats"
        ordering = ["-date"]

    def __str__(self):
        return f"Stats for {self.date}: {self.total_requests} requests"

    @property
    def cache_hit_rate(self):
        """Calculate cache hit rate percentage."""
        if self.total_requests == 0:
            return 0
        return (self.cached_requests / self.total_requests) * 100
