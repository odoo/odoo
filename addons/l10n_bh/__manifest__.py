{
    'name': 'Bahrain - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['bh'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Bahrain in Odoo.
===========================================================================
Bahrain accounting basic charts and localization.

Activates:
 - Chart of Accounts
 - Taxes
 - Tax reports
 - Fiscal Positions
 - States
    """,
    'depends': [
        'account',
        'l10n_gcc_invoice',
    ],
    'data': [
        'data/tax_report_full.xml',
        'data/tax_report_simplified.xml',
        'data/res.country.state.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
