# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spain - POS + TicketBAI",
    'version': '1.0',
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_es_edi_tbai',
        'l10n_es_pos',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_es_pos_tbai/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_es_pos_tbai/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
