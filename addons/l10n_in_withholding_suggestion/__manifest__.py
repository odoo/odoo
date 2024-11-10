{
    'name': "Indian - TDS and TCS Suggestion",
    'version': '1.0',
    'description': """
        Base module for Indian TDS (l10n_in_tds) & TCS (l10n_in_tcs).
    """,
    'category': 'Accounting/Localizations',
    'depends': ['l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'views/l10n_in_section_alert_views.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
    ],
    'license': 'LGPL-3',
}
