# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gelato",
    'summary': "Let new customers sign up for a newsletter during checkout",
    'description': """
        Allows easy integration with Gelato POD service.
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['sale', 'delivery'],
    'auto_install': True,
    'license': 'LGPL-3',
    'data': [
        'data/data.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml'
    ]
}
