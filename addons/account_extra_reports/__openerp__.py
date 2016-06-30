# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extra Accounting Reports',
    'version': '1.1',
    'category': 'Accounting',
    'description': """
Extra Accounting Reports.
====================================

This module adds two new reports:
* Sale/Purchase Journal report 
* Partner Ledger
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account_accountant'],
    'data': [
        'wizard/account_report_print_journal_view.xml',
        'views/report_journal.xml',
        'wizard/account_report_partner_ledger_view.xml',
        'views/report_partnerledger.xml',
        'data/account_report.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
