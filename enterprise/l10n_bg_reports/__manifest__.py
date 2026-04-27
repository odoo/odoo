# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Base module for Bulgarian reports
    """,
    'depends': [
        'l10n_bg',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
