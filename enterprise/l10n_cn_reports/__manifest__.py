# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'China - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for China
============================
    """,
    'depends': ['l10n_cn', 'account_reports'],
    'data': [
        'data/profit_and_loss_asbe.xml',
        'data/profit_and_loss_assbe.xml',
        'data/balance_sheet_asbe.xml',
        'data/balance_sheet_assbe.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_cn', 'account_reports'],
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
