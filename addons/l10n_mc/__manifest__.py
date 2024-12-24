# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Monaco - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mc'],
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Monaco.
""",
    'depends': [
        'l10n_fr_account',
        'account',
    ],
    'auto_install': ['account'],
    'license': 'LGPL-3',
}
