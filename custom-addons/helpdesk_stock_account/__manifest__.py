# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Stock Account',
    'category': 'Services/Helpdesk',
    'summary': 'Helpdesk, Stock, Account',
    'depends': ['helpdesk_stock', 'helpdesk_account'],
    'data': [
        'wizard/account_move_reversal_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
