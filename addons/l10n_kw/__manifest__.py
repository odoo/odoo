{
    'name': 'Kuwait - Accounting',
    'countries': ['kw'],
    'description': """
This is the base module to manage the accounting chart for Kuwait in Odoo.
==============================================================================
Kuwait accounting basic charts and localization.
Activates:
- Chart of accounts
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
