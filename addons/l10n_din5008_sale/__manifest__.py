# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008 - Sale',
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_din5008',
        'sale',
    ],
    'data': [
        'report/din5008_sale_templates.xml',
        'report/din5008_sale_order_layout.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
