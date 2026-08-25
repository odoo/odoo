{
    'name': 'Martinique - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mq'],
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Martinique.
""",
    'depends': [
        'l10n_fr_account',
        'account',
    ],
    'auto_install': ['account'],
    'license': 'LGPL-3',
}
