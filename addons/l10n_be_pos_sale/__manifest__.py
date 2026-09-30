# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'l10n_be_pos_sale',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Link module between pos_sale and l10n_be',
    'depends': ['pos_sale', 'l10n_be'],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_be_pos_sale/static/src/js/**/*',
        ],
        'web.assets_tests': [
            'l10n_be_pos_sale/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
