{
    'name': 'Bahrain - Point of Sale',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
Bahrain POS Localization
===========================================================
    """,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'depends': [
        'l10n_gcc_pos',
        'l10n_bh',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_bh_pos/static/src/**/*',
        ],
    },
    'auto_install': True,
}
