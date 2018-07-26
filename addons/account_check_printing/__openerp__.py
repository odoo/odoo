# -*- coding: utf-8 -*-
{
    'name': 'Check Printing Base',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Check printing commons',
    'description': """
This module offers the basic functionalities to make payments by printing checks.
It must be used as a dependency for modules that provide country-specific check templates.
The check settings are located in the accounting journals configuration page.
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends' : ['account'],
    'data': [
        'data/check_printing.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_journal_view.xml',
        'views/account_payment_view.xml',
        'wizard/print_pre_numbered_checks.xml'
    ],
    'installable': True,
    'auto_install': False,
}
