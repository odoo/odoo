# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Stock',
    'version': '1.0',
    'countries': ['pt'],
    'description': """Stock module for Portugal which allows hash and QR code on stock pickings""",
    'category': 'Accounting/Localizations/Stock',
    'depends': [
        'stock',
        'l10n_pt_account',
    ],
    'auto_install': [
        'stock',
        'l10n_pt_account',
    ],
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
        'views/report_delivery_slip.xml',
        'report/l10n_pt_stock_hash_integrity_templates.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
