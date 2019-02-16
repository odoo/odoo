# coding: utf-8

{
    'name': 'Saudi Arabia - Accounting',
    'version': '1.1',
    'author': 'DVIT.ME',
    'category': 'Localization',
    'description': """
Odoo Arabic localization for most arabic countries and Saudi Arabia.

This initially includes chart of accounts of USA translated to Arabic.

In future this module will include some payroll rules for ME .
""",
    'website': 'http://www.dvit.me',
    'depends': ['account', 'l10n_multilang'],
    'data': [
        'account.chart.template.xml',
        'account.account.template.csv',
        'account_chart_template_after.xml',
        'account_chart_template.yml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'load_translations',
}
