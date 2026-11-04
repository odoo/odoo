{
    'name': "Sénégal - Accounting",
    'countries': ['sn'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This module implements the taxes for Sénégal.
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
    'license': 'LGPL-3',
}
