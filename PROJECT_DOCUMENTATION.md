# Supermarket Promotional Offers REST API
## Project Documentation

## 1. Project Overview
The Supermarket Promotional Offers REST API allows supermarkets to register, publish promotional offers, and lets customers browse currently available deals. It uses a RESTful architecture and relational data storage.

### Objectives
- Register supermarket accounts.
- Allow authenticated supermarket owners to publish offers.
- Let users browse currently valid offers.
- Validate input and return appropriate HTTP status codes.
- Protect offer creation through authentication and ownership checks.
- Keep the implementation small, readable, and maintainable.

## 2. Technical Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python | Backend application logic |
| Framework | Flask | REST API routes |
| ORM | Flask-SQLAlchemy / SQLAlchemy | Database models and queries |
| Database | SQLite | Relational persistence for local development |
| Authentication | JWT | Authenticated offer creation |
| Password hashing | Werkzeug | Stores password hashes, not plaintext passwords |
| Frontend | HTML, CSS, JavaScript | Responsive offer browsing |
| Testing | pytest | Automated API tests |
| Manual testing | PowerShell or Postman | Verify HTTP requests and responses |

SQLite is easy to configure and suitable for this compact assignment. PostgreSQL can be considered for a larger production deployment.

## 3. Database Schema

The application uses two main tables: `supermarkets` and `offers`.

### 3.1 `supermarkets`

| Column | Type | Constraints / Description |
|---|---|---|
| `id` | Integer | Primary key |
| `name` | String(150) | Required |
| `email` | String(255) | Required and unique |
| `password_hash` | String(255) | Required password hash |
| `phone` | String(20) | Optional |
| `address` | Text | Required |
| `created_at` | DateTime | Registration timestamp |

### 3.2 `offers`

| Column | Type | Constraints / Description |
|---|---|---|
| `id` | Integer | Primary key |
| `supermarket_id` | Integer | Foreign key to `supermarkets.id` |
| `title` | String(200) | Required |
| `description` | Text | Optional |
| `discount_percent` | Numeric(5,2) | Greater than 0 and at most 100 |
| `start_date` | DateTime | Required offer start time |
| `end_date` | DateTime | Required; must be later than start |
| `created_at` | DateTime | Offer creation timestamp |

### 3.3 Relationship and availability
One supermarket can publish many offers (one-to-many). `offers.supermarket_id` references `supermarkets.id`, ensuring that an offer belongs to an existing supermarket.

An offer is available when the current UTC time is between its start and end timestamps, inclusive:

```sql
SELECT o.*, s.name AS supermarket_name
FROM offers AS o
JOIN supermarkets AS s ON s.id = o.supermarket_id
WHERE o.start_date <= CURRENT_TIMESTAMP
  AND o.end_date >= CURRENT_TIMESTAMP
ORDER BY o.end_date ASC;
```

The application applies this logic through SQLAlchemy and also supports search, discount/supermarket filters, and pagination.

## 4. Approach to Build the API

The request flow is:

1. **Client:** Browser frontend, PowerShell, or Postman sends an HTTP request.
2. **Routing:** Flask maps the URL and method to a route.
3. **Validation and access control:** The route validates JSON fields, data types, dates, authentication, and ownership as applicable.
4. **Data access:** SQLAlchemy queries or updates the relational database.
5. **Response:** The API returns JSON and an appropriate HTTP status code.

### Implementation steps
1. Configure Flask, SQLAlchemy, and SQLite.
2. Define `Supermarket` and `Offer` models.
3. Implement registration with validation and unique-email handling.
4. Implement login, verify password hashes, and issue a signed JWT.
5. Protect offer creation with JWT authentication and ownership checks.
6. Implement browsing with date filtering, search, discount filtering, and pagination.
7. Add consistent JSON errors and automated tests.
8. Build a responsive frontend that calls the browse endpoint.

## 5. Minimum Features of the Required Endpoints

### 5.1 Register a supermarket
**Endpoint:** `POST /api/supermarkets`

Minimum features:
- Accept name, email, password, and address; phone is optional.
- Validate required fields, email format, and field lengths.
- Hash the password before storing it.
- Reject duplicate email addresses.
- Return public supermarket information without exposing the password hash.

Example request:

```json
{
  "name": "Fresh Mart",
  "email": "owner@example.com",
  "password": "safe-pass-123",
  "phone": "9876543210",
  "address": "Hyderabad, Telangana"
}
```

**Success:** `201 Created`  
**Typical errors:** `400 Bad Request` for invalid input; `409 Conflict` for duplicate email.

### 5.2 Create an offer for a supermarket
**Endpoint:** `POST /api/supermarkets/{id}/offers`

Minimum features:
- Require a valid JWT bearer token.
- Allow owners to create offers only for their own supermarket.
- Validate title, discount, start date, and end date.
- Require end date to be later than start date.
- Store the offer and return its details.

Example request:

```json
{
  "title": "Weekend Grocery Sale",
  "description": "Discounts on selected grocery products",
  "discount_percent": 15,
  "start_date": "2026-10-23T00:00:00Z",
  "end_date": "2026-10-30T23:59:59Z"
}
```

**Success:** `201 Created`  
**Typical errors:** `400 Bad Request`, `401 Unauthorized` for a missing/invalid token, and `403 Forbidden` when the owner tries to publish for another supermarket.

### 5.3 Browse available offers
**Endpoint:** `GET /api/offers`

Minimum features:
- Return only offers currently within their validity window.
- Include the supermarket name with each offer.
- Return an empty list if no offers match.
- Support pagination and validate query parameters.
- Support optional search and discount/supermarket filters.

Example: `GET /api/offers?page=1&limit=10&q=grocery&min_discount=10`

**Success:** `200 OK`. Browsing is public in this implementation.

### Supporting endpoints
- `POST /api/auth/login` — returns a JWT after successful login.
- `GET /api/supermarkets` — lists public supermarket information.
- `GET /api/health` — application health check.

## 6. Endpoint Security

1. **Authentication:** Supermarket owners log in to obtain a JWT.
2. **Authorization:** The token identifies the owner; the URL supermarket ID must match the authenticated account.
3. **Password hashing:** Werkzeug hashes passwords instead of storing plaintext.
4. **Input validation:** Validate required fields, email, lengths, discount bounds, and date ordering.
5. **Database integrity:** Unique email and foreign-key constraints protect data consistency.
6. **Safe errors:** Return concise JSON messages without exposing stack traces.
7. **Secret management:** Use strong, randomly generated JWT and application secrets through environment variables; do not use development fallback secrets in production.
8. **HTTPS:** Encrypt production traffic.
9. **Rate limiting:** Limit repeated login and registration attempts in production.
10. **CORS:** If hosted separately, allow only trusted frontend origins.

The JWT expires after two hours. A production version should also consider key rotation, monitoring, secure logging, and account-recovery processes.

## 7. Frontend Design Approach

The frontend uses HTML, CSS, and JavaScript. It is lightweight, responsive, and focused on helping customers find deals.

### Main components
- **Header:** OfferFinder brand and short description.
- **Search field:** Searches offer title, description, or supermarket name.
- **Minimum-discount filter:** Narrows the results.
- **Offer cards:** Display discount, title, supermarket name, description, and expiry.
- **Loading and empty states:** Communicate progress and no-result cases.
- **Responsive grid:** Adapts to desktop and mobile screens.

### Request flow
1. The page calls `GET /api/offers` when it loads.
2. Search and filter values are sent as query parameters.
3. Returned offers are rendered as cards.
4. Errors and empty results are displayed clearly.

API text is escaped before insertion into the page. React could be introduced later for reusable components, routing, and more complex state management.

## 8. Additional Features and Future Enhancements

| Feature | Benefit |
|---|---|
| Offer categories | Organize groceries, beverages, household items, etc. |
| Location-based browsing | Help users find nearby deals |
| Offer updates and deactivation | Let owners manage outdated offers |
| Favorites | Let customers save offers |
| Expiry notifications | Remind customers before offers expire |
| Admin moderation | Review supermarket accounts and offers |
| Product images | Make offers easier to recognize |
| Usage analytics | Measure views and engagement |
| PostgreSQL deployment | Support a larger production workload |
| Rate limiting and monitoring | Reduce abuse and improve operations |

A practical next step would be offer update/deactivation endpoints, followed by categories and location-based discovery.

## 9. Testing and Verification

The project includes pytest tests for:
- Successful supermarket registration.
- Duplicate-email rejection.
- Password validation.
- Authenticated offer creation and browsing.
- Rejection of unauthenticated offer creation.
- Invalid discount rejection.

The current automated test suite has been run successfully with **5 tests passing**. Manual testing has also confirmed that an offer can be created and returned by the browse endpoint.

Before final submission, add or manually verify:
- Future offers are excluded until their start time.
- Expired offers are excluded.
- A supermarket cannot create offers for another supermarket.
- Invalid or expired JWTs are rejected.
- Pagination and search filters work correctly.

## 10. Conclusion

The Supermarket Promotional Offers REST API provides a working foundation for supermarket registration, secure offer publishing, and public browsing of valid promotions. Flask provides the backend framework, SQLite supplies relational storage, SQLAlchemy manages data access, JWT authentication protects offer creation, and a lightweight frontend presents current offers.

The implementation is intentionally compact and readable, with validation, access checks, documentation, and automated tests. Future work could add moderation, location-based search, offer management, notifications, and a production database.
