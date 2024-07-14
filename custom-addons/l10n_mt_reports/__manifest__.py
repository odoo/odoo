# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Malta - Accounting Reports",
    'countries': ['mt'],
    "version": "1.0",
    'category': 'Accounting/Localizations/Reporting',
    "description": """
Malta accounting reports.
====================================================
-Profit and Loss
-Balance Sheet
""",
    "depends": ['l10n_mt', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_mt', 'account_reports'],
    'license': 'OEEL-1',
}
