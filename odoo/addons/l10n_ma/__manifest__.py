# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Morocco - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ma'],
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Morocco.

This module has been built with the help of Caudigef.
""",
    'depends': [
        'base',
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
