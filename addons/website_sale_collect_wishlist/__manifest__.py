# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Availability Notifications',
    'category': 'Website/Website',
    'summary': 'Bridge module for Website sale collect and wishlist',
    'description': """
It allows adding products to the wishlist when pickup location is not found
    """,
    'depends': [
        'website_sale_wishlist',
        'website_sale_collect',
    ],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_collect_wishlist/static/src/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
