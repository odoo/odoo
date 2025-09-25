# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Shopper's Wishlist",
    'summary': 'Allow shoppers to enlist products',
    'description': """
Allow shoppers of your eCommerce store to create personalized collections of products they want to buy and save them for future reference.
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale'],
    'data': [
        'security/ir_rule.xml',
        'security/ir.model.access.csv',

        'views/templates.xml',
        'views/svg_templates.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'website_sale_wishlist/static/src/interactions/**/*',
            'website_sale_wishlist/static/src/scss/**/*',
            'website_sale_wishlist/static/src/js/**/*',
        ],
        'web.assets_tests': [
            'website_sale_wishlist/static/tests/**/*',
        ],
        'website.website_builder_assets': [
            'website_sale_wishlist/static/src/website_builder/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
