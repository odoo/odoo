{
    'name': 'Indian - Accounting Asset',
    'version': '1.0',
    'description': """
Accounting Asset for India
================================
    """,
    'category': 'Accounting/Localizations/Asset',
    'depends': [
        'l10n_in',
        'account_asset',
    ],
    'data': [
        'views/account_asset_view.xml',
        'views/account_modify_views.xml',
    ],
    'auto_install': ['l10n_in', 'account_asset'],
    'installable': True,
    'license': 'OEEL-1',
}
