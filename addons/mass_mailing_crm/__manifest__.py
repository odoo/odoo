# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on lead / opportunities',
    'category': 'Marketing/Email Marketing',
    'summary': 'Add lead / opportunities UTM info on mass mailing',
    'description': """UTM and mass mailing on lead / opportunities""",
    'depends': ['crm', 'mass_mailing'],
    'data': [
        'views/mailing_mailing_views.xml',
    ],
    'demo': [
        'demo/mailing_mailing.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mass_mailing_crm/static/src/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
