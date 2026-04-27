# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Automatic Transfers',
    'depends': ['account_accountant'],
    'description': """
Account Automatic Transfers
===========================
Manage automatic transfers between your accounts.
    """,
    'category': 'Accounting/Accounting',
    'data': [
        'security/account_auto_transfer_security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/transfer_model_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
