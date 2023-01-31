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
        'wizard/account_invoice_send_views.xml',
        'wizard/snailmail_confirm_invoice_views.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'snailmail_account/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
