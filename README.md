# Smart Shopper 🛒
An intelligent Django REST API that provides near real-time product search using SerpAPI’s Google Shopping results. Optimized with async calls, Redis caching, and basic analytics tracking.

https://github.com/user-attachments/assets/b99cd640-a033-4581-806c-2aa376930708


## 🚀 Quick Start
```bash
uv init
# activate the venv
uv sync
python manage.py migrate
python manage.py runserver
```
### Quick API Test
```bash
# Search for products
curl "http://127.0.0.1:8000/api/products/search/?q=365+WholeFoods+Peanut+Butter&limit=10"

# Check API health
curl "http://127.0.0.1:8000/health/"
```
## Report 

### Approach 
I started by clarifying the core requirement: return structured product cards fast for any product query. I planned a pipeline: async fetch from SerpAPI → parse & normalize product fields → cache in Redis → serve via Django REST endpoint. Prioritized speed and resilience: async HTTP client, short timeouts, caching, and basic analytics to spot slow queries.

### Solution
- Built a services.py SerpAPI client using httpx with async requests, timeouts, and retries.
- Implemented parsing routines to extract title, brand, price, weight, images, and product links from SerpAPI responses.
- Added Redis caching with a configurable TTL plus cache-hit tracking for analytics.
- Exposed a REST endpoint in Django (DRF) that accepts q and limit, checks cache, or fetches live and then returns normalized JSON.

### Challenges
- Django API not running at first — the server wouldn’t boot. Turned out I missed a couple of local steps (migrations and environment variables). After running python manage.py migrate and fixing the .env settings (SERPAPI_KEY and Redis URL), the API started. The failure felt like a ghost bug but was just missing setup steps — added clearer README steps to avoid this.
- SerpAPI reliability & costs — inconsistent results and rate limits meant I had to add timeouts, retries, and a caching layer to avoid hammering the API.
- Parsing edge cases — product cards vary by retailer; added normalization and fallback parsing rules to make fields more robust.

### Experiments/Improvements
- Manual scraping fallback: implement optional lightweight scrapers for high-value queries to reduce SerpAPI costs. Use responsible scraping, caching, and obey robots.txt. This saves API cost but adds maintenance and legal checks.
- Ranking & deduplication: merge duplicate product cards from multiple retailers and rank by price + seller reliability.
- Advanced caching strategies: adaptive TTLs based on query popularity and stale-while-revalidate behavior.
- Pagination & streaming: support partial responses/streaming for faster first results.
- Analytics UI: small dashboard for cache hits, top queries, and slow requests.
- Tests & CI: add unit tests for parsing logic, integration tests (mocked SerpAPI), and a GitHub Actions pipeline.
