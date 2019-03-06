# -*- coding: utf-8 -*-
{
    'name': "snailmail_account",
    'description': """
Allows users to send invoices by post
=====================================================
        """,
    'category': 'Tools',
    'version': '0.1',
    'depends': ['account', 'snailmail'],
    'data': [
        'views/res_config_settings_views.xml',
        'wizard/account_invoice_send_views.xml',
    ],
    'auto_install': True,
}
