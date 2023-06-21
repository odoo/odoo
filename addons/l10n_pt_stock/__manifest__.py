# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Stock',
    'version': '1.0',
    'countries': ['pt'],
    'description': """Stock module for Portugal which allows hash and QR code on delivery notes""",
    'category': 'Accounting/Localizations/Stock',
    'depends': [
        'stock',
        'blockchain',
        'l10n_pt',
    ],
    'data': [
        'report/l10n_pt_stock_blockchain_integrity.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'auto_install': [
        'stock',
        'l10n_pt'
    ],
    'license': 'LGPL-3',
}
