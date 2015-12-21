# coding: utf-8

{
    'name': 'Saudi Arabia - Accounting',
    'version': '1.1',
    'author': 'DVIT.ME',
    'category': 'Localization/Account Charts',
    'description': """
Odoo Arabic localization for most arabic countries and Saudi Arabia.

This initially includes chart of accounts of USA translated to Arabic.

In future this module will include some payroll rules for ME .
""",
    'website': 'http://www.dvit.me',
    'depends': ['account_chart', 'l10n_multilang'],
    'data': [
        'account_type.xml',
        'account.account.template.csv',
        'account.chart.template.xml',
        'wizard.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
