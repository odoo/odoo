{
    'name': 'WooCommerce Connector',
    'version': '19.0.1.0.0',
    'category': 'Sales/Channel Integration',
    'summary': 'Sync WooCommerce products, orders, customers, and inventory with Odoo',
    'description': """
WooCommerce Connector for Odoo 19
==================================
Full bidirectional integration between Odoo and WooCommerce stores.

Features
--------
- WooCommerce REST API v3 client with retry, rate-limit handling, and pagination
- Product import (simple & variable) with SKU-first deduplication
- Product variant support with attribute mapping
- Customer import with billing/shipping address handling
- Order import with auto-confirm, line item resolution, shipping lines
- Inventory push (Odoo stock levels → WooCommerce)
- Webhook receiver for real-time updates
- Full sync audit log (channel.sync.log)
- Binding models for clean external-ID tracking
- Cron jobs for scheduled sync
- Admin UI with smart buttons, sync status, and sync log drill-down
- Multi-company ready
- Canada-first: province/country code mapping for CA/US

Architecture
------------
Built on channel_base, an abstract foundation that can support future
channels (Amazon, Walmart, etc.) without refactoring.

Sync Flow
---------
WooCommerce → Odoo:
  Cron / Webhook → API client → Mapper → Binding → Odoo record

Odoo → WooCommerce:
  Stock move confirmed → Inventory sync → API client → WooCommerce stock
    """,
    'author': 'Custom',
    'depends': [
        'channel_base',
        'product',
        'sale',
        'sale_management',
        'sales_team',
        'stock',
        'contacts',
        'mail',
    ],
    'data': [
        'security/woocommerce_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/woocommerce_backend_views.xml',
        'views/woocommerce_binding_views.xml',
        'views/woocommerce_wizard_views.xml',
        'views/woocommerce_menus.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'assets': {},
}
