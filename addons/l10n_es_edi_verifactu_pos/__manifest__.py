# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spain - Veri*Factu for Point of Sale',
    'version': '1.0',
    'category': 'Accounting/Localizations/Point of Sale',
    'summary': "Add Veri*Factu support to Point of Sale",
    'depends': [
        'l10n_es_edi_verifactu',
        'point_of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_es_edi_verifactu_pos/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_es_edi_verifactu_pos/static/tests/tours/*'
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
