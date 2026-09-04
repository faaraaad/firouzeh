# Firouzeh Shortener &mdash; High-Performance Django URL Shortener

A production-grade, highly reliable URL Shortener service built in Python & Django. It converts long URLs into compact **5-character** Base62 links, features sub-millisecond in-memory caching for rapid redirection, supports idempotent deduplication, and provides comprehensive automated test suites.

---

## 🌟 Key Features

1. **5-Character Base62 Short Codes**:
   - Strictly enforces $\le 5$ character short codes using Base62 alphabet (`[0-9a-zA-Z]`).
   - Accommodates $62^5 = 916,132,832$ (~916 million) unique permanent URLs.
   - Deterministic SHA-256 hash mapping with collision probing.

2. **Ultra-Fast Redirection & Scalability**:
   - **In-Memory Caching (LocMem / Redis-ready)**: Serves cached redirect lookups in `<1ms` without querying the database on repeat requests.
   - **Database Indexing**: Unique B-tree index on `short_code` and hash index on `url_hash` for $O(1)$ query time.
   - **Deduplication**: Submitting the same long URL reuses the existing short code.

3. **Robust Input Validation & Security**:
   - Protocol sanitization (`http://` / `https://`).
   - Anti-loop protection: Prevents self-referential shortening.
   - Safe HTTP redirect codes (`302 Found` default for accurate analytics, configurable to `301`).

4. **REST API & Interactive Web UI**:
   - Modern, responsive dark-mode glassmorphic web interface.
   - Standard JSON REST API for seamless programmatic integration.
   - Real-time click counting and last accessed timestamp tracking.

---

## 📐 Design Justification & Architectural Choices

### Why Base62 for 5-Character Constraint?
- Standard Base64 contains characters like `+`, `/`, or `=` which are URL-unsafe or require percent-encoding.
- Base62 uses only alphanumeric characters (`0-9`, `a-z`, `A-Z`), which are completely URL-safe across all browsers, SMS, and email clients.
- $62^5 = 916,132,832$ combinations satisfy the 5-character constraint while providing massive capacity.

### Storage & Collision Strategy
- `url_hash` (SHA-256): Long URLs can span thousands of characters, which makes indexing slow and exceeds standard database index limits. By storing a 64-character SHA-256 hash with an index, lookups for deduplication remain fast and lightweight.
- **Collision Resolution**: If a short code collision occurs, a deterministic salt probing mechanism increments until a free slot is identified within an atomic transaction.

### Framework Choice (Django vs FastAPI)
- **FastAPI** is fast for raw async microservices; however, **Django** provides a complete, battle-tested ecosystem with:
  - Built-in ORM with robust migration management.
  - Multi-backend caching framework (in-memory, Memcached, Redis).
  - Production-ready Admin dashboard for inspecting, searching, and managing shortened links out-of-the-box.
  - Security middlewares (CSRF, Clickjacking, Host validation).

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Virtual environment

### 2. Installation
```bash
# Clone or navigate to the repository
cd /Users/farhad/Downloads/firouzeh

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Migrations & Start Server
```bash
# Apply migrations
python manage.py migrate

# Start development server
python manage.py runserver 127.0.0.1:8000
```

Access the web UI at: **`http://127.0.0.1:8000/`**

---

## 📡 REST API Reference

### 1. Shorten a URL
- **Endpoint**: `POST /api/shorten/`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "url": "https://www.example.com/very/long/article?ref=social"
  }
  ```
- **Response (201 Created / 200 OK)**:
  ```json
  {
    "status": "success",
    "short_code": "mK89a",
    "short_url": "http://127.0.0.1:8000/mK89a",
    "original_url": "https://www.example.com/very/long/article?ref=social",
    "is_new": true,
    "created_at": "2026-09-02T16:30:00.000000+00:00"
  }
  ```

### 2. Redirect to Original URL
- **Endpoint**: `GET /<short_code>`
- **Behavior**: Returns `HTTP 302 Found` with `Location: <original_url>`. Increments click count.

### 3. Retrieve Link Statistics
- **Endpoint**: `GET /api/urls/<short_code>/stats/`
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "short_code": "mK89a",
    "short_url": "http://127.0.0.1:8000/mK89a",
    "original_url": "https://www.example.com/very/long/article?ref=social",
    "clicks_count": 14,
    "created_at": "2026-09-02T16:30:00.000000+00:00",
    "last_accessed_at": "2026-09-02T16:45:12.000000+00:00"
  }
  ```

---

## 🧪 Testing

Run all unit and integration tests using either `manage.py test` or `pytest`:

```bash
# Run with Django test runner
python manage.py test shortener

# Or run with pytest
pytest
```

### Test Coverage includes:
- Base62 integer encoder/decoder round-trip accuracy.
- URL shortening API with 201 Created and JSON schema validation.
- Short code $\le 5$ character length constraint enforcement.
- HTTP 302 redirection to original target URL.
- 400 Bad Request on invalid/malformed URL inputs.
- 404 Not Found on non-existent short codes.
- Idempotent deduplication (same URL $\rightarrow$ same short code).
- In-memory cache hit verification.
- Real-time click counter and stats verification.
