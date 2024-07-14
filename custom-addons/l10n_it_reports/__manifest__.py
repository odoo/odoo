# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - Accounting Reports',
    'countries': ['it'],
    'version': '1.0',
    'description': """
Accounting reports for Italy
============================

    """,
    'category': 'Accounting/Accounting',
    'depends': ['l10n_it', 'account_reports'],
    'data': [
        'data/account_profit_and_loss_data.xml',
        'data/account_balance_sheet_report_data.xml',
        'data/account_reduce_balance_sheet_report_data.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    'auto_install': ['l10n_it', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
