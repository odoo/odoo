# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'Invoicing',
    'version' : '1.1',
    'author' : 'OpenERP SA',
    'summary': 'Send Invoices and Track Payments',
    'sequence': 4,
    'description': """
Invoicing & Payments
====================
The specific and easy-to-use Invoicing system in Odoo allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your suppliers and customers. 

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. This module also offers you an easy method of registering payments, without having to encode complete abstracts of account.
    """,
    'category' : 'Accounting & Finance',
    'website': 'https://www.odoo.com/page/billing',
    'images' : ['images/accounts.jpeg','images/bank_statement.jpeg','images/cash_register.jpeg','images/chart_of_accounts.jpeg','images/customer_invoice.jpeg','images/journal_entries.jpeg'],
    'depends' : ['base_setup', 'product', 'analytic', 'board', 'report', 'web_tip'],
    'data': [
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'views/account_menuitem.xml',
        'report/account_invoice_report_view.xml',
        'report/account_entries_report_view.xml',
        'report/account_analytic_entries_report_view.xml',
        'views/account_installer.xml',
        'wizard/account_reconcile_view.xml',
        'wizard/account_unreconcile_view.xml',
        'wizard/account_statement_from_invoice_view.xml',
        'views/account_view.xml',
        'views/account_report.xml',
        'views/account_financial_report_data.xml',
        'wizard/account_report_common_view.xml',
        'wizard/account_invoice_refund_view.xml',
        'wizard/account_move_line_reconcile_select_view.xml',
        'wizard/account_move_line_unreconcile_select_view.xml',
        'wizard/account_move_reversal_view.xml',
        'wizard/account_state_open_view.xml',
        'wizard/account_validate_move_view.xml',
        'wizard/account_report_general_ledger_view.xml',
        'wizard/account_invoice_state_view.xml',
        'wizard/account_report_partner_balance_view.xml',
        'wizard/account_report_account_balance_view.xml',
        'wizard/account_report_aged_partner_balance_view.xml',
        'wizard/account_report_partner_ledger_view.xml',
        'wizard/account_register_payment_view.xml',
        'wizard/pos_box.xml',
        'views/account_end_fy.xml',
        'views/account_invoice_view.xml',
        'data/account_data.xml',
        'data/data_account_type.xml',
        'data/configurable_account_chart.xml',
        'data/invoice_action_data.xml',
        'views/account_invoice_workflow.xml',
        'views/partner_view.xml',
        'views/product_view.xml',
        'views/account_assert_test.xml',
        'views/account_analytic_view.xml',
        'views/company_view.xml',
        'views/account_bank_view.xml',
        'views/res_config_view.xml',
        'views/account_tip_data.xml',
        'test/account_pre_install.yml',
        'views/report_invoice.xml',
        'views/report_trialbalance.xml',
        'views/report_overdue.xml',
        'views/report_partnerbalance.xml',
        'views/report_agedpartnerbalance.xml',
        'views/report_partnerledger.xml',
        'views/report_financial.xml',
        'views/report_generalledger.xml',
        'views/report_configurator.xml',
        'views/report_followup.xml',
        'views/account.xml',
    ],
    'qweb' : [
        "static/src/xml/account_reconciliation.xml",
        "static/src/xml/account_payment.xml",
    ],
    'demo': [
        'demo/account_demo.xml',
        'demo/account_minimal.xml',
        'demo/account_invoice_demo.xml',
        'demo/account_bank_statement.xml',
        'views/account_unit_test.xml',
    ],
    'test': [
#         'test/account_report.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
