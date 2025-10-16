# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Availability Notifications',
    'category': 'Website/Website',
    'summary': 'Bridge module for Website sale comparison and wishlist',
    'description': """
It allows for comparing products from the wishlist
    """,
    'depends': [
        'website_sale_comparison',
        'website_sale_wishlist',
    ],
    'data': [
        'views/templates.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
