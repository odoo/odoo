# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bangladesh - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['bd'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Bangladesh in Odoo
==============================================================================

Bangladesh accounting basic charts and localization.

Activates:

- Chart of accounts
- Taxes
""",
    'depends': [
        'account',
        'l10n_account_withholding_tax',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account.account.tag.csv',
        'views/menu_items.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
