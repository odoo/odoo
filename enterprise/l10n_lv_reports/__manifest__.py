# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Latvia - Accounting Reports",
    "version": "1.0",
    'category': 'Accounting/Localizations/Reporting',
    "description": """
Latvia accounting reports.
====================================================
-Profit and Loss
-Balance Sheet
""",
    "depends": ['l10n_lv', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_lv', 'account_reports'],
    'license': 'OEEL-1',
}
