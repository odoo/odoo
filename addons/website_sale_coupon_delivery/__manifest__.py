# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Free Delivery with Coupon on eCommerce",
    'summary': """Allows to offer free shippings in coupon reward on eCommerce""",
    'description': """Allows to offer free shippings in coupon reward on eCommerce""",
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale_delivery', 'sale_coupon_delivery'],
    'data': [
        'views/website_sale_coupon_delivery_templates.xml',
    ],
    'auto_install': True,
}
