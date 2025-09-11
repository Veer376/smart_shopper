# Smart Shopper 🛒

A intelligent Django REST API that provides real-time product search capabilities using SerpAPI's Google Shopping integration. Built with performance optimization, caching, and comprehensive analytics.


https://github.com/user-attachments/assets/b99cd640-a033-4581-806c-2aa376930708


## 🚀 Quick Start

### Installation

1. **Clone the project:**

2. **Install dependencies:**

```bash
uv sync
```

3. **Configure environment:**

   - Add your SerpAPI key to `mysite/settings.py`
   - Ensure Redis is running for caching

4. **Run migrations:**

```bash
python manage.py migrate
```

5. **Start the development server:**

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`

### Quick API Test

```bash
# Search for products
curl "http://127.0.0.1:8000/api/products/search/?q=365+WholeFoods+Peanut+Butter&limit=10"

# Check API health
curl "http://127.0.0.1:8000/health/"
```

## 🏗️ Project Structure

```
smart_shopper/
├── mysite/                    # Django project settings
│   ├── settings.py           # Configuration and SerpAPI settings
│   ├── urls.py              # Main URL routing
│   └── wsgi.py              # WSGI configuration
├── shopping_api/             # Main application
│   ├── models.py            # Database models (Product, Cache, Analytics)
│   ├── services.py          # SerpAPI client and business logic
│   ├── views.py             # REST API endpoints
│   ├── urls.py              # API URL routing
│   └── migrations/          # Database migrations
├── db.sqlite3               # SQLite database
├── manage.py                # Django management script
└── pyproject.toml           # Project dependencies
```

## 🔍 SerpAPI Features & Implementation

### Core SerpAPI Integration

Our implementation leverages **SerpAPI's Google Shopping API** with the following key features:

#### **Request Limits & Optimization**

- **Max Results per Request**: 100 products (configurable via `limit` parameter)
- **Default Results**: 20 products per request
- **Rate Limiting**: Built-in connection pooling and async handling
- **Timeout Configuration**: 10-second timeout for API requests

#### **Smart Caching System**

- **Cache TTL**: Configurable cache expiration (default in settings)
- **Cache Hit Tracking**: Monitors cache usage for optimization
- **Auto Cache Cleanup**: Expired entries are automatically removed
- **Performance Metrics**: Response time tracking for both cached and live requests

#### **Product Data Extraction**

From SerpAPI responses, we extract and structure:

- **Basic Info**: Title, Product ID, Source, Brand
- **Pricing**: Current price, old price, price extraction and normalization
- **Quality Metrics**: Ratings (1-5 scale), review counts, snippets
- **Media**: Product thumbnails and images
- **Metadata**: Weight, category, delivery info, badges
- **Links**: Direct product links to retailers

#### **Analytics & Monitoring**

- **Search Query Tracking**: Popular searches and frequency analysis
- **API Usage Statistics**: Daily request counts, cache hit rates
- **Performance Monitoring**: Average response times, error tracking
- **Usage Optimization**: Identifies patterns to improve caching strategies

### API Endpoint Details

#### **Product Search**

```
GET /api/products/search/
```

**Parameters:**

- `q` (required): Product search query
- `limit` (optional): Number of results (1-100, default: 20)

**Example Requests:**

```bash
# Basic search
GET /api/products/search/?q=iPhone+15

# Limited results
GET /api/products/search/?q=wireless+headphones&limit=50

# Specific product search
GET /api/products/search/?q=365+Organic+Peanut+Butter
```

**Response Format:**

```json
{
  "query": "iPhone 15",
  "results": [
    {
      "title": "Apple iPhone 15 128GB",
      "product_id": "12345",
      "price": "$799.00",
      "extracted_price": 799.0,
      "rating": 4.5,
      "reviews": 1250,
      "source": "Apple Store",
      "product_link": "https://...",
      "thumbnail": "https://...",
      "brand": "Apple"
    }
  ],
  "count": 20,
  "cached": false,
  "response_time_ms": 450,
  "api_version": "1.0.0"
}
```

## 🛠️ Technologies Used

- **Backend**: Django 5.0+ with Django REST Framework
- **Database**: SQLite (development), PostgreSQL ready
- **Caching**: Redis for high-performance caching
- **HTTP Client**: httpx for async API requests
- **Search API**: SerpAPI Google Shopping integration
- **Configuration**: python-decouple for environment management

## 📊 Key Features

- ⚡ **Async Processing**: Non-blocking SerpAPI requests
- 🗄️ **Intelligent Caching**: Reduces API calls and improves response times
- 📈 **Analytics Dashboard**: Track usage patterns and optimize performance
- 🔒 **Error Handling**: Robust error handling with fallback responses
- 🎯 **Rate Limiting**: Prevent API abuse and manage costs
- 📱 **RESTful API**: Clean, documented API endpoints
- 🔍 **Advanced Search**: Leverages Google Shopping's comprehensive database

## 🚦 Error Handling

The API implements comprehensive error handling:

- **400 Bad Request**: Missing or invalid query parameters
- **503 Service Unavailable**: SerpAPI service issues
- **500 Internal Server Error**: Unexpected server errors

All error responses include helpful messages and maintain consistent JSON structure.

## 📝 License

This project is for educational and development purposes. Please ensure compliance with SerpAPI's terms of service when using in production.
