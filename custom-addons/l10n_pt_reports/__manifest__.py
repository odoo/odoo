# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Portugal - Accounting Reports',
    'countries': ['pt'],
    'version': '1.0',
    'description': """
Accounting reports for Portugal
================================

    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_pt', 'account_reports'],
    'data': [
        'data/profit_loss.xml',
        'data/balance_sheet.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    'auto_install': ['l10n_pt', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
