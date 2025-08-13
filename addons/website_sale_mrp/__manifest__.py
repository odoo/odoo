# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Kit Availability',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Manage Kit product inventory & availability',
    'description': """
Manage the inventory of your Kit products and display their availability status in your eCommerce store.
    """,
    'depends': [
        'website_sale_stock',
        'sale_mrp',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_sale_mrp/static/src/js/**/*',
        ],
        'web.assets_tests': [
            'website_sale_mrp/static/tests/tours/*',
        ],
    },
    'license': 'LGPL-3',
}
