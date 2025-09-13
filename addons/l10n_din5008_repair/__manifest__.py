# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008 - Repair',
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_din5008',
        'repair',
    ],
    'data': [
        'report/din5008_repair_order_layout.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
