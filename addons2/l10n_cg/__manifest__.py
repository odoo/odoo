{
    'name': 'Congo - Accounting',
    'category': 'Accounting/Localizations/Account Charts',
    'countries': ['cg'],
    'description': """
This module implements the tax for Congo.
===========================================================

The Chart of Accounts is from SYSCOHADA.

    """,
    'depends': [
        'l10n_syscohada',
    ],
    'data': [
        'data/account_tax_report_data.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
