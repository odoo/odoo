# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesia - Point of Sale',
    'version': '1.0',
    'description': """Indonesian Point of Sale""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_id',
        'point_of_sale'
    ],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_id_pos/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_id_pos/static/tests/**/*'
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
