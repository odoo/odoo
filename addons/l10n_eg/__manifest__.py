# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Egypt - Accounting",
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/egypt.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['eg'],
    'description': """
Egypt Accounting Module
==============================================================================
Egypt Accounting Basic Charts and Localization.

Activates:

- Chart of Accounts
- Taxes
- VAT Return
- Withholding Tax Report
- Schedule Tax Report
- Other Taxes Report
- Fiscal Positions
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'views/account_tax.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml',
    ],
    'license': 'LGPL-3',
}
