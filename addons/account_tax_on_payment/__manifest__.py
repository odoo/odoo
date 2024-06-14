# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tax on Payment',
    'version': '1.0',
    'description': """
Tax on payment
==============
Tax calculation in payment is always include.
When payment is match with Invoice/Bill then reverse entry is created automatically.
    """,
    'category': 'Accounting/Accounting',
    'depends': ['account'],
    'data': [
        'views/account_payment_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': False,
    'license': 'LGPL-3',
}
