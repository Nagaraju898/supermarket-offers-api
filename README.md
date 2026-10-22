# Supermarket Offers REST API

A small, runnable REST API for supermarket registration, offer publishing, and browsing active promotional offers. Includes a lightweight public web page, JWT authentication for supermarket owners, SQLite storage, validation, and pytest tests.

## Stack

- Python 3.10+
- Flask and Flask-SQLAlchemy
- SQLite (default; PostgreSQL can be configured with `DATABASE_URL`)
- JWT bearer tokens
- pytest
- HTML, CSS, and JavaScript frontend

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:JWT_SECRET = "replace-with-a-different-long-random-secret"
python app.py
```

Open http://127.0.0.1:5000 for the offers browser. API health check: `GET /api/health`.

On macOS/Linux, activate the virtual environment with `source .venv/bin/activate`.

**Before production:** set strong random secrets in environment variables, set `FLASK_DEBUG` off, use HTTPS, and configure a production WSGI server. Do not use the built-in development server in production.

## Database schema

### `supermarkets`
- `id`: integer primary key
- `name`: required string (max 150)
- `email`: required unique string (max 255)
- `password_hash`: required password hash (never stores plaintext password)
- `phone`: optional string
- `address`: required text
- `created_at`: timestamp

### `offers`
- `id`: integer primary key
- `supermarket_id`: required foreign key to `supermarkets.id`
- `title`: required string (max 200)
- `description`: optional text
- `discount_percent`: numeric discount greater than 0 and at most 100
- `start_date`, `end_date`: required timestamps; end must be later than start
- `created_at`: timestamp

Relationship: one supermarket has many offers. Offers are deleted with their owning supermarket.

## API endpoints

### 1. Register a supermarket

`POST /api/supermarkets`

```json
{
  "name": "Fresh Mart",
  "email": "owner@example.com",
  "password": "safe-pass-123",
  "phone": "9876543210",
  "address": "Hyderabad, Telangana"
}
```

Returns `201 Created`. Email must be unique; password must be at least 8 characters.

### 2. Log in (to receive a token)

`POST /api/auth/login`

```json
{"email":"owner@example.com","password":"safe-pass-123"}
```

Returns an `access_token` valid for two hours.

### 3. Create an offer

`POST /api/supermarkets/1/offers`

Header: `Authorization: Bearer <access_token>`

```json
{
  "title": "Weekend Grocery Sale",
  "description": "Discounts on selected groceries",
  "discount_percent": 15,
  "start_date": "2026-10-23T00:00:00Z",
  "end_date": "2026-10-30T23:59:59Z"
}
```

The authenticated supermarket can create offers only for its own account.

### 4. Browse available offers

`GET /api/offers?page=1&limit=10`

Optional query parameters:
- `q`: search title, description, or supermarket name
- `supermarket_id`: filter by supermarket ID
- `min_discount`: minimum discount percentage
- `page`: page number (default 1)
- `limit`: results per page (1–100; default 10)

Only offers whose start and end times include the current UTC time are returned.

### 5. List registered supermarkets

`GET /api/supermarkets`

### 6. Health check

`GET /api/health`

## Example workflow with curl

Register:

```bash
curl -X POST http://127.0.0.1:5000/api/supermarkets \
  -H "Content-Type: application/json" \
  -d '{"name":"Fresh Mart","email":"owner@example.com","password":"safe-pass-123","address":"Hyderabad, India"}'
```

Login:

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"safe-pass-123"}'
```

Copy the returned token into `TOKEN`, then create an offer:

```bash
curl -X POST http://127.0.0.1:5000/api/supermarkets/1/offers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"title":"Weekend Sale","description":"Selected products","discount_percent":15,"start_date":"2026-10-23T00:00:00Z","end_date":"2026-10-30T23:59:59Z"}'
```

Browse:

```bash
curl "http://127.0.0.1:5000/api/offers?page=1&limit=10"
```

## Tests

```powershell
pytest -q
```

## Security and validation

- Passwords are hashed with Werkzeug.
- JWT authentication is required to publish offers.
- Ownership checks prevent a supermarket from publishing for another account.
- Required fields, email, lengths, discount bounds, and date ordering are validated.
- Duplicate email returns `409 Conflict`.
- API errors return JSON without stack traces.
- Use HTTPS, strong secrets, rate limiting, restricted CORS, and a production WSGI server before deployment.

## Frontend design

The public homepage displays current offers as responsive cards. Visitors can search by offer or supermarket name and filter by minimum discount. The frontend escapes text before rendering to reduce DOM-based injection risks.

## Possible future enhancements

- Offer categories and product images
- Location-based offer discovery
- Favorites and expiry notifications
- Admin moderation and offer approval
- Supermarket profile editing and offer update/deactivation endpoints
- Audit logs and usage analytics
- PostgreSQL for production deployments
