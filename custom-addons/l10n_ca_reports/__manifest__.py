# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Canada - Accounting Reports',
    'countries': ['ca'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Canada
    """,
    'depends': [
        'l10n_ca',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
