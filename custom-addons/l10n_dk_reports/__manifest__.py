# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Denmark - Accounting Reports',
    'countries': ['dk'],
    'version': '1.0',
    'author': 'Odoo House ApS',
    'website': 'https://odoohouse.dk',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Denmark
=================================
    """,
    'depends': [
        'l10n_dk',
        'account_reports',
        'account_saft',
        'documents_account',
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
        'data/account_report_ec_sales_list_report.xml',
        'data/saft_report.xml',
        'data/documents_file_data.xml',
        'views/account_journal_dashboard.xml',
    ],
    'auto_install': [
        'l10n_dk',
        'account_reports',
    ],
    'license': 'OEEL-1',
}
