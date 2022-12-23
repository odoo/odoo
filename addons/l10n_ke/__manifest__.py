# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Kenya - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/kenya.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ke'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This provides a base chart of accounts and taxes template for use in Odoo.
    """,
    'depends': [
        'account',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
