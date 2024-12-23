# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mauritania - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mr'],
    'description': """
Mauritania basic package that contains the chart of accounts, the taxes, tax reports, etc.
    """,
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
