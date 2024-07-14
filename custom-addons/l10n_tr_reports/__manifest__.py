# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Turkey - Accounting Reports',
    'countries': ['tr'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Turkey
    """,
    'depends': [
        'l10n_tr', 'account_reports'
    ],
    'data': [
        'data/account_report_tr_balance_sheet_data.xml',
        'data/account_report_tr_pnl_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
