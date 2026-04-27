{
    'name': 'Indian - Accounting Reports',
    'version': '1.1',
    'description': """
Accounting reports for India
================================
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': [
        'l10n_in',
        'account_reports',
        'sign',
    ],
    'data': [
        'data/account_financial_html_report_gstr1.xml',
        'data/account_financial_html_report_gstr3b.xml',
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
        'views/account_move_views.xml',
    ],
    'auto_install': ['l10n_in', 'account_reports'],
    'installable': True,
    'post_init_hook': '_l10n_in_reports_post_init',
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'l10n_in_reports/static/src/components/**/*',
        ],
    },
}
