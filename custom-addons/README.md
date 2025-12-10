# SMART Marketplace - Odoo 18 Modules

This repository contains custom Odoo 18 modules for implementing a production-ready multi-vendor marketplace with social commerce integrations.

## 📦 Modules Overview

### Core Modules

1. **smart_marketplace_core** (Base Module)
   - Seller management with KYC workflow
   - Product extensions for marketplace
   - Commission engine
   - Multi-seller order management
   - REST API endpoints for products

2. **smart_marketplace_payout**
   - Payout batch creation and processing
   - Commission calculation
   - Accounting entries for payouts
   - Automated payout generation (cron)

3. **smart_marketplace_delivery**
   - Sha6er delivery integration
   - Shipment tracking
   - OTP verification and delivery proofs
   - Webhook handling for status updates

4. **smart_social_scheduler**
   - Social media post queue management
   - Scheduled posting to multiple channels
   - Post status tracking
   - Retry logic for failed posts

## 🚀 Installation

### Prerequisites

- Odoo 18.0
- PostgreSQL database
- Python 3.10+

### Required Odoo Modules

The following Odoo modules must be installed:

- `base`
- `website_sale`
- `sale_management`
- `stock`
- `account`
- `portal`
- `mail`
- `rating`
- `delivery`

### Installation Steps

1. **Update Odoo Configuration**

   Ensure your `odoo.conf` or `myodoo.cfg` includes the custom-addons path:
   ```ini
   addons_path = /path/to/odoo/odoo/addons,/path/to/odoo/addons,/path/to/odoo/custom-addons
   ```

2. **Install Modules**

   Install modules in the following order:
   ```
   1. smart_marketplace_core
   2. smart_marketplace_payout
   3. smart_marketplace_delivery
   4. smart_social_scheduler
   ```

3. **Configure Settings**

   - Go to **Settings > Marketplace**
   - Configure Sha6er API credentials (for delivery module)
   - Set up commission rules
   - Configure social media connectors

## 📋 Module Dependencies

```
smart_marketplace_core
├── base
├── website_sale
├── sale_management
├── stock
├── account
├── portal
├── mail
└── rating

smart_marketplace_payout
├── smart_marketplace_core
└── account

smart_marketplace_delivery
├── smart_marketplace_core
├── delivery
└── stock

smart_social_scheduler
├── smart_marketplace_core
└── mail
```

## 🔧 Configuration

### Sha6er Integration

1. Go to **Settings > Companies**
2. Select your company
3. Enter Sha6er API Key and API URL
4. Save

### Commission Configuration

1. Go to **Marketplace > Sellers**
2. Select a seller
3. Set Commission Type (Percentage or Fixed)
4. Set Commission Value
5. Save

### Social Media Setup

1. Configure social media connectors (requires additional module: `smart_social_connector`)
2. Connect seller accounts to social channels
3. Schedule posts via **Marketplace > Social Posts**

## 📡 REST API Endpoints

### Products

- `GET /smart/api/products` - List products with filters
  - Query params: `q`, `page`, `per_page`, `category_id`, `seller_id`, `price_min`, `price_max`, `in_stock`
  
- `GET /smart/api/products/{id}` - Get product details

### Webhooks

- `POST /smart/webhook/delivery` - Sha6er delivery status updates

## 🔐 Security

- Sellers can only access their own products, orders, and payouts
- Portal users have restricted access based on seller association
- Admin/Manager groups have full access to all marketplace data

## 🧪 Testing

To test the modules:

1. Create a test seller account
2. Complete KYC documents
3. Submit for approval
4. Create products
5. Create test orders
6. Generate payouts
7. Test delivery integration

## 📝 Features Implemented

### ✅ Completed

- [x] Seller management with KYC workflow
- [x] Product marketplace extensions
- [x] Commission calculation
- [x] Payout batch processing
- [x] Sha6er delivery integration
- [x] Social post queue management
- [x] REST API for products
- [x] Security rules and access control
- [x] Basic views and menus

### 🚧 To Be Implemented

- [ ] Full social media connectors (Facebook, Instagram, TikTok, LinkedIn, WhatsApp)
- [ ] Payment gateway integrations (Bankily, Sedad, Stripe, PayPal)
- [ ] Mobile API with JWT authentication
- [ ] Analytics and reporting dashboards
- [ ] Advanced multi-seller checkout
- [ ] Product rating and reviews
- [ ] Dispute management
- [ ] Automated email/WhatsApp notifications

## 🐛 Known Issues

- Social connector service placeholder (requires `smart_social_connector` module)
- Payment gateway integrations not yet implemented
- Some views may need refinement based on specific requirements

## 📚 Documentation

For detailed functional specifications, see `llm.txt` in the project root.

## 🤝 Contributing

When adding new features:

1. Follow Odoo coding standards
2. Add security rules for new models
3. Include unit tests where applicable
4. Update this README with new features

## 📄 License

LGPL-3

## 👥 Support

For issues or questions, please contact the development team.

---

**Version:** 18.0.1.0.0  
**Last Updated:** 2024

