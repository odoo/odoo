# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Free Delivery with Coupon & Loyalty on eCommerce",
    'summary': """Allows to offer free shippings in loyalty program rewards on eCommerce""",
    'description': """Allows to offer free shippings in loyalty program rewards on eCommerce""",
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale_delivery', 'website_sale_loyalty', 'sale_loyalty_delivery'],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_sale_loyalty_delivery/static/src/**/*',
        ],
        'web.assets_tests': [
            'website_sale_loyalty_delivery/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
