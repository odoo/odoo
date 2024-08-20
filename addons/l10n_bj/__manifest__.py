{
    'name': "Benin - Accounting",
    'countries': ['bj'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This module implements the tax for Benin.
=================================================================

The Chart of Accounts is from SYSCOHADA.

    """,
    'depends': [
        'l10n_syscohada',
    ],
    'auto_install': ['l10n_syscohada'],
    'data': [
        'data/account_tax_report_data.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
