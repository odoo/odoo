# -*- coding: utf-8 -*-
{
    'name': "Snail Mail - Account",
    'description': """
Allows users to send invoices by post
=====================================================
        """,
    'category': 'Hidden/Tools',
    'version': '0.1',
    'depends': ['account', 'snailmail'],
    'data': [
        'views/res_config_settings_views.xml',
        'wizard/account_move_send_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
