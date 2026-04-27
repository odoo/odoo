# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Republic of Korea - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Base module for the Republic of Korea reports
    """,
    'depends': [
        'l10n_kr',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet.xml',
        "data/profit_loss.xml",
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
