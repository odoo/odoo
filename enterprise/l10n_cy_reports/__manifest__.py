{
    "name": "Cyprus - Accounting Reports",
    "version": "1.0",
    "category": "Accounting/Localizations/Reporting",
    "description": """
Cyprus accounting reports
=========================
- Profit and Loss
- Balance sheet
    """,
    "depends": [
        "l10n_cy",
        "account_reports",
    ],
    "data": [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    "installable": True,
    "auto_install": [
        "l10n_cy",
        "account_reports",
    ],
    "license": "OEEL-1"
}
