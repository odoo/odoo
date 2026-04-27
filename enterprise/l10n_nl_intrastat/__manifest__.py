# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Netherlands Intrastat Declaration',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Generates Netherlands Intrastat report for declaration based on invoices.
    """,
    'depends': ['l10n_nl_reports', 'account_intrastat'],
    'data': [
        'data/account_report_ec_sales_list_report.xml',
        'views/res_company_view.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
