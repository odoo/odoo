# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gelato",
    'summary': "Let new customers sign up for a newsletter during checkout",
    'description': """
        Allows easy integration with Gelato POD service.
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['sale'],
    'auto_install': True,
    'license': 'LGPL-3',
    'data': [
        'views/product_views.xml'
    ]
}
