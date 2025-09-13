# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008 - Stock',
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_din5008',
        'stock',
    ],
    'data': [
        'report/din5008_stock_picking_layout.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
