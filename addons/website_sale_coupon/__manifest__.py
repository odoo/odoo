# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Coupons & Promotions for eCommerce",
    'summary': """Use coupon & promotion programs in your eCommerce store""",
    'description': """
Create coupon and promotion codes to share in order to boost your sales (free products, discounts, etc.). Shoppers can use them in the eCommerce checkout.

Coupon & promotion programs can be edited in the Catalog menu of the Website app.
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale', 'website_links', 'sale_coupon'],
    'data': [
        'security/ir.model.access.csv',
        'views/coupon_share_views.xml',
        'views/website_sale_templates.xml',
        'views/res_config_settings_views.xml',
        'views/sale_coupon_coupon_views.xml',
        'views/sale_coupon_program_views.xml',
    ],
    'auto_install': ['website_sale', 'sale_coupon'],
    'assets': {
        'web.assets_frontend': [
            'website_sale_coupon/static/src/js/coupon_toaster_widget.js',
        ],
        'web.assets_tests': [
            'website_sale_coupon/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
