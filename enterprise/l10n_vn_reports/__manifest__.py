# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Vietnam - Accounting Reports',
    "summary": """
Accounting reports for the Vietnam
    """,
    "version": "1.0",
    "category": "Accounting/Localizations/Reporting",
    "license": "OEEL-1",
    "depends": [
        "l10n_vn",
        "account_reports",
    ],
    "data": [
        "data/account_tax_report_data.xml",
        "data/balance_sheet.xml",
        "data/profit_and_loss.xml",
    ],
    "installable": True,
    "auto_install": True,
}
