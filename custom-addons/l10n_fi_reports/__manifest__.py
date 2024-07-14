# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Finland - Accounting Reports',
    'countries': ['fi'],
    'version': '1.1',
    'description': """
Accounting reports for Finland
================================

    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_fi', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
        'data/account_report_ec_sales_list_report.xml',
    ],
    'auto_install': ['l10n_fi', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}
