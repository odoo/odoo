{
    'name': "Ivory Coast - Accounting",
    'countries': ['ci'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This module implements the taxes for Ivory Coast.
=================================================================

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
