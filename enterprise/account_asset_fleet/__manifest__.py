# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Assets/Fleet bridge',
    'category': 'Accounting/Accounting',
    'summary': 'Manage assets with fleets',
    'version': '1.0',
    'depends': ['account_fleet', 'account_asset'],
    'data': [
        'views/account_asset_views.xml',
        'views/account_move_views.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
