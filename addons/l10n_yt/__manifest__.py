{
    'name': 'Mayotte - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['yt'],
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Mayotte.
""",
    'depends': [
        'l10n_fr_account',
        'account',
    ],
    'auto_install': ['account'],
    'license': 'LGPL-3',
}
