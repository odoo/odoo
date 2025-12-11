# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMART eCommerce Extension',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Enhanced eCommerce with delivery zones, product extensions and REST API',
    'description': """
SMART eCommerce Extension Module
=================================

This module extends Odoo's eCommerce functionality with:
- Extended product fields (brand, model, specifications, video URL)
- Availability status computation (in_stock, low_stock, out_of_stock)
- Website filters (brand, price range, availability)
- Enhanced product cards (second image hover, stock badges)
- Dynamic estimated delivery date
- Delivery zones with city-based pricing
- REST API endpoints for products, cart, checkout, and payment
- Marketplace seller management with KYC verification

Features:
---------
1. Product Template Extensions
   - Brand and Model fields
   - HTML Specifications
   - Video URL support
   - Automatic availability status

2. Website Sale Enhancements
   - Brand filter on shop page
   - Price range slider
   - Availability filter
   - Hover image on product cards
   - Stock status badges

3. Delivery Zone Management
   - Zone-based delivery pricing
   - City mapping
   - Weight-based extra charges
   - Estimated delivery calculation

4. REST API
   - GET /smart/api/products - Product listing
   - GET/POST /smart/api/cart - Cart management
   - POST /smart/api/checkout - Checkout process
   - POST /smart/api/payment/callback - Payment webhook

5. Marketplace Sellers
   - Seller registration and profile management
   - KYC document upload and verification
   - Approval workflow (draft/pending/approved/suspended)
   - Portal views: Dashboard, Orders, Payments
   - Commission management
    """,
    'author': 'SMART Marketplace',
    'website': 'https://smartmarketplace.com',
    'depends': [
        'base',
        'mail',
        'portal',
        'website_sale',
        'sale_management',
        'stock',
        'delivery',
        'smart_marketplace_core',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        
        # Data
        'data/delivery_zone_data.xml',
        'data/analytics_cron.xml',
        'data/cart_abandonment_sequence.xml',
        
        # Views (Backend)
        'views/product_template_views.xml',
        'views/delivery_zone_views.xml',
        'views/sale_order_views.xml',
        'views/analytics_views.xml',
        'views/marketplace_seller_views.xml',
        'views/menus.xml',
        
        # Website Templates
        'views/website_templates.xml',
        'views/seller_portal_templates.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'smart_ecommerce_extension/static/src/scss/shop.scss',
            'smart_ecommerce_extension/static/src/js/shop.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'icon': '/smart_ecommerce_extension/static/description/icon.svg',
}

