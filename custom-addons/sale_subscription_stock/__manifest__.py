# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Sale Subscriptions Stock',
    'version': '1.0',
    'depends': ['sale_subscription', 'sale_stock'],
    'category': 'Sales/Subscriptions',
    'summary': 'Allow to create recurring order on storable product',
    'description': """Sale Subscriptions Stock

Sale Subscription Stock is a bridge module between sale_subscription and
sale_stock. The purpose of this module is to allow the user to create
subscription sale order with storable product which will result in
recurring delivery order and invoicing of those products.
Features:
- Allow the creation of recurring storable product
- Automaticaly create delivery order for the recurring storable product
- Invoice delivered recurring product at the end of invoicing period
- Report planned delivery for active subscriptions
""",
    'website': 'https://www.odoo.com/app/subscriptions',
    'data': [
        'views/product_template_views.xml',
    ],
    'demo': [
        'data/sale_subscription_stock_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'sale_subscription_stock/static/src/*',
        ],
    },
    'license': 'OEEL-1',
}
