{
    'name': 'Guyana - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['gf'],
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Guiana.
""",
    'depends': [
        'l10n_fr_account',
        'account',
    ],
    'auto_install': ['account'],
    'license': 'LGPL-3',
}
