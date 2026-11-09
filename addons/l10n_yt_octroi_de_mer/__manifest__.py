{
    'name': 'Mayotte - Octroi de mer',
    'icon': '/account/static/description/l10n.png',
    'author': 'Odoo SA',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Bridge module to auto install l10n_fr_octroi_de_mer with l10n_yt.
""",
    'depends': [
        'l10n_yt',
        'l10n_fr_octroi_de_mer',
    ],
    'auto_install': ['l10n_yt'],
    'license': 'LGPL-3',
}
