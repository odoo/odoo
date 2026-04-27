# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Cambodia - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Base module for the Cambodian reports
    """,
    'depends': [
        'l10n_kh',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet_kh.xml',
        'data/form_wt003.xml',
        'data/profit_and_loss_kh.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
