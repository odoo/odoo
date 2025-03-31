# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United Arab Emirates - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/united_arab_emirates.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ae'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
United Arab Emirates Accounting Module
=======================================================
United Arab Emirates accounting basic charts and localization.

Activates:

- Chart of Accounts
- Taxes
- Tax Report
- Fiscal Positions
    """,
    'depends': [
        'base',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/l10n_ae_data.xml',
        'data/account_tax_report_data.xml',
        'data/res.bank.csv',
        'views/report_invoice_templates.xml',
        'views/account_move.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
