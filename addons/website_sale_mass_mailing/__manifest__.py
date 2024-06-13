# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Checkout Newsletter",
    'summary': "Let new customers sign up for a newsletter during checkout",
    'description': """
        Allows anonymous shoppers of your eCommerce to sign up for a newsletter during the checkout
        process.
    """,
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale', 'website_mass_mailing'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
