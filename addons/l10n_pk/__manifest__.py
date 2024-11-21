# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Pakistan - Accounting',
    'website': 'https://www.odoo.com/documentation/saas-17.2/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pk'],
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
<<<<<<< saas-17.2
    'description': ' This is the base module to manage chart of accounts and localization for the Pakistan ',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
||||||| 994c50671e6dc694d869fe27b385002634432dcd
    'description': ' This is the base module to manage chart of accounts and localization for the Pakistan ',
    'depends': [
        'account',
    ],
=======
    'description': """
Pakistan Accounting Module
=======================================================
Pakistan accounting basic charts and localization.

Activates:

- Chart of Accounts
- Taxes
- Tax Report
- Withholding Tax Report
    """,
    'depends': ['account'],
>>>>>>> a5c4643dc81b7dccdf2bf32bd82233edc664585e
    'data': [
        'data/account_tax_vat_report.xml',
        'data/account_tax_wh_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
