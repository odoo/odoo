{
    "name": "Indian - TDS TCS Reports",
    "version": "1.0",
    "description": """
TDS TCS Reports Handler
    """,
    "category": "Accounting/Localizations/Reporting",
    "depends": ["l10n_in_reports", "l10n_in_withholding"],
    "data": [
        "data/account_tax_report_tds_tcs_data.xml",
    ],
    "auto_install": ["l10n_in_reports", "l10n_in_withholding"],
    "installable": True,
    "license": "OEEL-1",
    'assets': {
        'web.assets_backend': [
            'l10n_in_reports_tds_tcs/static/src/components/**/*',
        ],
    },
}
