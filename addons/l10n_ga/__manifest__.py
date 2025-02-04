{
    'name': "Gabon - Accounting",
    'countries': ['ga'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This module implements the tax for Gabon.
=================================================================

The Chart of Accounts is from SYSCOHADA.

    """,
    'depends': [
        'l10n_syscohada',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
