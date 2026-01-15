# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Collect & Wishlist",
    'category': 'Website/Website',
    'summary': "Bridge module between Click & Collect and Wishlist",
    'description': """
Allow users to add a product to wishlist if the product is not available for the selected pickup location.
    """,
    'depends': ['website_sale_wishlist', 'website_sale_collect'],
    'data': [
        'views/delivery_form_templates.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
