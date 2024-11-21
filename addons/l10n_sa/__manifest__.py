# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi Arabia - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['sa'],
    'version': '2.0',
    'author': 'Odoo S.A., DVIT.ME (http://www.dvit.me)',
    'category': 'Accounting/Localizations/Account Charts',
<<<<<<< saas-17.2
    'description': """
Odoo Arabic localization for most Saudi Arabia.
""",
<<<<<<< saas-17.4
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/saudi_arabia.html',
||||||| a9ae7f5bb0f978d40a99389c048edb5ddb397339
    'website': 'https://www.odoo.com/documentation/saas-17.2/applications/finance/fiscal_localizations/saudi_arabia.html',
=======
    'website': 'https://www.odoo.com/documentation/saas-17.2/applications/finance/fiscal_localizations/saudi_arabia.html',
||||||| 994c50671e6dc694d869fe27b385002634432dcd
    'description': """
Odoo Arabic localization for most Saudi Arabia.
""",
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/saudi_arabia.html',
=======
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/saudi_arabia.html',
    'description': """
Saudi Arabia Accounting Module
===========================================================
Saudi Arabia Accounting Basic Charts and Localization

Activates:

- Chart of Accounts
- Taxes
- Vat Filling Report
- Withholding Tax Report
- Fiscal Positions
""",
>>>>>>> a5c4643dc81b7dccdf2bf32bd82233edc664585e
>>>>>>> acb5273b9893073c98ea85fe64c33e47bd4a6982
    'depends': [
        'l10n_gcc_invoice',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_data.xml',
        'data/account_tax_report_data.xml',
        'data/report_paperformat_data.xml',
        'views/report_invoice.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
