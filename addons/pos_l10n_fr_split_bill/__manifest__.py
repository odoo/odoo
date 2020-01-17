# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'French Pos certification bill splitting',
    'version': '1.0',
    'category': 'Sales/Point Of Sale',
    'summary': 'Restaurant bill splitting extension for the French Point of Sale ',
    'description': """
 """,
    'depends': ['pos_restaurant', 'l10n_fr_pos_cert'],
    'data': [
        'views/pos_assets.xml',
    ],
    'installable': True,
    'auto_install': True,
}
