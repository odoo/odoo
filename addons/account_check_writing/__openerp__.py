# -*- coding: utf-8 -*-
{
    'name': 'Check Writing',
    'version': '1.0',
    'author': 'Odoo SA',
    'category': 'Generic Modules/Accounting',
    'summary': 'Keep Track of Checks Payments',
    'description': """
Check Writing
=============
This module allows to register your payments by check in odoo.
You can also print checks by installing a module that adds country-specific check printing.
The check settings are located in the accounting journals configuration page.
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends' : ['account_accountant'],
    'data': [
        'data/check_writing.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_journal_view.xml',
        'views/account_payment_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
