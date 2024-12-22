# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bangladesh - Accounting',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['bd'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': ' This is the base module to manage chart of accounts and localization for the Bangladesh ',
    'depends': [
        'account',
    ],
    'data': [
        'data/account.account.tag.csv',
        'data/res.country.state.csv',
        'data/account_tax_report_data.xml',
        'views/menu_items.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
