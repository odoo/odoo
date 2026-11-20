{
    'name': 'Reunion - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['re'],
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Réunion.
""",
    'depends': [
        'l10n_fr_account',
        'account',
    ],
    'data': [
        'data/res_country_group_data.xml',
    ],
    'auto_install': ['account'],
    'license': 'LGPL-3',
}
