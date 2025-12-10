# SMART Marketplace API Documentation

## Overview

Complete REST API specification for SMART Marketplace mobile applications, serving both:

- **Buyer App**: For customers browsing products, placing orders, and tracking deliveries
- **Seller App**: For vendors managing products, orders, and payouts

## Quick Links

- **Swagger YAML**: [`swagger.yaml`](./swagger.yaml)
- **Base URL (Production)**: `https://api.smartmarketplace.com/v1`
- **Base URL (Staging)**: `https://staging-api.smartmarketplace.com/v1`
- **Base URL (Local)**: `http://localhost:8068/smart/api`

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

Obtain tokens via `/auth/login` or `/auth/register` endpoints.

## API Endpoints Summary

### 🔐 Authentication (Buyer & Seller)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | User login |
| POST | `/auth/register` | User registration |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/password/reset` | Request password reset |
| POST | `/auth/password/confirm` | Confirm password reset |
| POST | `/auth/logout` | User logout |

### 📦 Products (Buyer App)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List products with filters |
| GET | `/products/{id}` | Get product details |
| GET | `/products/{id}/reviews` | Get product reviews |
| POST | `/products/{id}/reviews` | Add product review |
| GET | `/products/featured` | Get featured products |
| GET | `/products/bestsellers` | Get bestselling products |

### 📂 Categories

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories` | List all categories |
| GET | `/categories/{id}` | Get category details |
| GET | `/categories/{id}/products` | Get products in category |

### 🛒 Cart (Buyer App)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/cart` | Get cart contents |
| POST | `/cart` | Add item to cart |
| DELETE | `/cart` | Clear cart |
| PUT | `/cart/items/{item_id}` | Update cart item quantity |
| DELETE | `/cart/items/{item_id}` | Remove cart item |
| POST | `/cart/apply-coupon` | Apply discount coupon |

### 💳 Checkout (Buyer App)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/checkout` | Create order |
| POST | `/checkout/validate` | Validate checkout details |
| POST | `/checkout/payment/initiate` | Initiate payment |
| POST | `/checkout/payment/callback` | Payment webhook callback |

### 📋 Orders (Buyer App)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders` | List customer orders |
| GET | `/orders/{id}` | Get order details |
| POST | `/orders/{id}/cancel` | Cancel order |
| GET | `/orders/{id}/tracking` | Get tracking info |
| POST | `/orders/{id}/reorder` | Reorder previous items |

### 👤 User Profile (Buyer App)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/user/profile` | Get user profile |
| PUT | `/user/profile` | Update profile |
| POST | `/user/profile/avatar` | Upload avatar |
| GET | `/user/addresses` | List addresses |
| POST | `/user/addresses` | Add address |
| PUT | `/user/addresses/{id}` | Update address |
| DELETE | `/user/addresses/{id}` | Delete address |
| PUT | `/user/password` | Change password |

### ❤️ Wishlist (Buyer App)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/wishlist` | Get wishlist |
| POST | `/wishlist` | Add to wishlist |
| DELETE | `/wishlist/{product_id}` | Remove from wishlist |

### 🚚 Delivery

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/delivery/zones` | List delivery zones |
| POST | `/delivery/calculate` | Calculate delivery cost |
| GET | `/delivery/estimate` | Get delivery estimate |

---

## Seller App APIs

### 🔐 Seller Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/seller/auth/register` | Register as seller |
| POST | `/seller/auth/login` | Seller login |
| POST | `/seller/kyc/submit` | Submit KYC documents |
| GET | `/seller/kyc/status` | Get KYC status |

### 📦 Seller Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/seller/products` | List seller products |
| POST | `/seller/products` | Create product |
| GET | `/seller/products/{id}` | Get product details |
| PUT | `/seller/products/{id}` | Update product |
| DELETE | `/seller/products/{id}` | Delete product |
| POST | `/seller/products/{id}/images` | Upload product images |
| PUT | `/seller/products/{id}/stock` | Update stock |
| POST | `/seller/products/bulk-update` | Bulk update products |

### 📋 Seller Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/seller/orders` | List seller orders |
| GET | `/seller/orders/{id}` | Get order details |
| PUT | `/seller/orders/{id}/status` | Update order status |
| POST | `/seller/orders/{id}/ship` | Mark as shipped |
| GET | `/seller/orders/{id}/print` | Print invoice/packing slip |

### 📊 Seller Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/seller/dashboard` | Get dashboard overview |
| GET | `/seller/dashboard/sales` | Get sales statistics |
| GET | `/seller/dashboard/notifications` | Get notifications |

### 💰 Seller Payouts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/seller/payouts` | List payout history |
| GET | `/seller/payouts/balance` | Get balance info |
| POST | `/seller/payouts/request` | Request payout |
| GET | `/seller/payouts/accounts` | List payout accounts |
| POST | `/seller/payouts/accounts` | Add payout account |

### 🏪 Seller Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/seller/profile` | Get seller profile |
| PUT | `/seller/profile` | Update profile |
| PUT | `/seller/profile/store` | Update store settings |
| GET | `/seller/reviews` | Get reviews |
| POST | `/seller/reviews/{id}/respond` | Respond to review |

---

## Response Format

All API responses follow this standard format:

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful",
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Invalid input data",
    "fields": {
      "email": ["Email is required"],
      "password": ["Password must be at least 8 characters"]
    }
  }
}
```

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Input validation failed |
| 500 | Server Error - Internal error |

## Rate Limiting

- **Public endpoints**: 100 requests/minute
- **Authenticated endpoints**: 300 requests/minute

Rate limit headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

## Payment Methods

Supported payment methods:
- `bankily` - Bankily mobile payment
- `sedad` - Sedad payment gateway
- `cash_on_delivery` - Cash on delivery

## Viewing the API Documentation

### Option 1: Swagger UI (Online)
Upload `swagger.yaml` to [Swagger Editor](https://editor.swagger.io/)

### Option 2: Local Swagger UI
```bash
# Using Docker
docker run -p 8080:8080 -e SWAGGER_JSON=/api/swagger.yaml -v $(pwd):/api swaggerapi/swagger-ui
```

### Option 3: Postman
Import `swagger.yaml` directly into Postman for testing.

## Integration Examples

### Login (cURL)

```bash
curl -X POST "http://localhost:8068/smart/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Get Products (cURL)

```bash
curl -X GET "http://localhost:8068/smart/api/products?category_id=1&page=1&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

### Add to Cart (JavaScript)

```javascript
const response = await fetch('/smart/api/cart', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  },
  body: JSON.stringify({
    product_id: 123,
    quantity: 2
  })
});
const data = await response.json();
```

### Create Order (JavaScript)

```javascript
const response = await fetch('/smart/api/checkout', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  },
  body: JSON.stringify({
    shipping_address_id: 1,
    delivery_zone_id: 2,
    payment_method: 'bankily',
    notes: 'Please call before delivery'
  })
});
const order = await response.json();
```

## SDK Generation

Generate client SDKs using OpenAPI Generator:

```bash
# Generate TypeScript SDK
openapi-generator generate -i swagger.yaml -g typescript-axios -o ./sdk/typescript

# Generate Swift SDK (iOS)
openapi-generator generate -i swagger.yaml -g swift5 -o ./sdk/ios

# Generate Kotlin SDK (Android)
openapi-generator generate -i swagger.yaml -g kotlin -o ./sdk/android

# Generate Dart SDK (Flutter)
openapi-generator generate -i swagger.yaml -g dart -o ./sdk/flutter
```

## Support

For API support or issues:
- Email: api-support@smartmarketplace.com
- Documentation: https://smartmarketplace.com/api-docs

---

**Version**: 1.0.0  
**License**: LGPL-3.0

