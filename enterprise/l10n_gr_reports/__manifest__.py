# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Greece - Accounting Reports',
    'version': '1.0',
    'description': """
Accounting reports for Greece
================================

    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': [
        'l10n_gr',
        'account_reports',
    ],
    'data': [
        'data/balance_sheet-gr.xml',
        'data/profit_and_loss-gr.xml',
        'data/ec_sales_list_report-gr.xml',
    ],
    'post_init_hook': '_l10n_gr_reports_post_init',
    'installable': True,
    'auto_install': ['l10n_gr', 'account_reports'],
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
