# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Availability Notifications',
    'category': 'Website/Website',
    'summary': 'Notify the user when a product is back in stock',
    'description': """
Allow the user to select if he wants to receive email notifications when a product of his wishlist gets back in stock.
    """,
    'depends': [
        'website_sale_stock',
        'website_sale_wishlist',
    ],
    'data': [
        'views/website_sale_stock_wishlist_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_stock_wishlist/static/src/interactions/**/*',
            'website_sale_stock_wishlist/static/src/scss/**/*',
            'website_sale_stock_wishlist/static/src/xml/**/*',
            (
                'before',
                'website_sale/static/src/interactions/website_sale.js',
                'website_sale_stock_wishlist/static/src/js/variant_mixin.js',
            ),
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
