# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Uzbekistan - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['uz'],
    'description': """
Uzbekistan Accounting: Chart of Account.
========================================

Uzbekistan accounting chart and localization.
  """,
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'base_vat',
    ],
    'demo': [
        'demo/demo_company.xml'
    ],
    'data': [
        'data/account.account.tag.csv'
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
