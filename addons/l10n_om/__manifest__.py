{
    'name': 'Oman - Accounting',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Oman Accounting Module
=================================================================
Oman accounting basic charts and localization.
Activates:
- Chart of Accounts
- Taxes
- VAT Return
- Fiscal Positions
- States
""",
    'countries': ['om'],
    'depends': [
        'account',
    ],
    'auto_install': True,
    'data': [
        'data/res.country.state.csv',
        'data/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
