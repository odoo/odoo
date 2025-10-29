# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Checkout Newsletter",
    'summary': "Let new customers sign up for a newsletter during checkout",
    'description': """
        Allows anonymous shoppers of your eCommerce to sign up for a newsletter during the checkout
        process.
    """,
    'category': 'Website/Website',
    'depends': ['website_sale', 'website_mass_mailing', 'mass_mailing_sale'],
    'assets': {
        'mass_mailing.assets_builder': [
            'website_sale_mass_mailing/static/src/builder/**/*',
        ],
    },
    'data': [
        'views/res_config_settings_views.xml',
        'views/templates.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
