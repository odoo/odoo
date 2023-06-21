# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Point of Sale',
    'version': '1.0',
    'countries': ['pt'],
    'description': """Point of Sale module for Portugal which allows hash and QR code on POS orders""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'point_of_sale',
        'blockchain',
        'l10n_pt',
    ],
    'data': [
        'report/l10n_pt_pos_blockchain_integrity.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_pt_pos/static/src/js/pos.js',
            'l10n_pt_pos/static/src/js/ReceiptScreen.js',
            'l10n_pt_pos/static/src/js/ClosePosPopup.js',
            'l10n_pt_pos/static/src/js/OrderReceipt.js',
            'l10n_pt_pos/static/src/xml/OrderReceipt.xml',
        ],
    },
    'installable': True,
    'auto_install': [
        'point_of_sale',
        'l10n_pt'
    ],
    'license': 'LGPL-3',
}
