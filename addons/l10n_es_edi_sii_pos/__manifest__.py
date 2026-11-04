# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spain - Point of Sale + SII",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_es_edi_sii',
        'point_of_sale',
    ],
    'data': [
        'receipt/pos_order_receipt.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_es_edi_sii_pos/static/src/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
