# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on sale orders',
    'category': 'Marketing/Email Marketing',
    'summary': 'Add sale order UTM info on mass mailing',
    'description': """UTM and mass mailing on sale orders""",
    'depends': ['sale', 'mass_mailing'],
    'assets': {
        'mass_mailing.assets_builder': [
            'mass_mailing_sale/static/src/builder/**/*',
        ],
    },
    'data': [
        'views/mailing_mailing_views.xml',
        'views/snippets_themes.xml',
        'views/templates/snippets/s_product_snapshot.xml',
    ],
    'demo': [
        'demo/mailing_mailing.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
