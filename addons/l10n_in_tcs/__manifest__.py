{
    'name': "Indian - TCS",
    'version': '1.0',
    'countries': ['in'],
    'description': """
        Support for Indian TCS (Tax Collected at Source).
    """,
    'category': 'Accounting/Localizations',
    'depends': ['l10n_in_withholding_suggestion'],
    'data': [
        'data/l10n_in.section.alert.csv',
        'data/account_tax_report_tcs_data.xml',
        'views/account_move_views.xml',
        'views/account_move_line_views.xml',
    ],
    'post_init_hook': '_l10n_in_tcs_post_init',
    'license': 'LGPL-3',
}
