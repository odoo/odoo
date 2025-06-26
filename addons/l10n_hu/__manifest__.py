# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Hungary - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['hu'],
    'version': '3.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Accounting chart and localization for Hungary
    """,
    'depends': [
        'account',
        'base_vat',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'data/res.bank.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
