# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spain - Veri*Factu for Point of Sale',
    'category': 'Accounting/Localizations/Point of Sale',
    'summary': "Add Veri*Factu support to Point of Sale",
    'depends': [
        'l10n_es_edi_verifactu',
        'point_of_sale',
    ],
    'data': [
        'views/pos_order_views.xml',
        'receipt/pos_order_receipt.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_es_edi_verifactu_pos/static/src/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
