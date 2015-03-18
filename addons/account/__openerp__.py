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
    'name' : 'eInvoicing',
    'version' : '1.1',
    'author' : 'OpenERP SA',
    'category' : 'Accounting & Finance',
    'description' : """
Accounting and Financial Management.
====================================

Financial and accounting module that covers:
--------------------------------------------
    * General Accounting
    * Cost/Analytic accounting
    * Third party accounting
    * Taxes management
    * Budgets
    * Customer and Supplier Invoices
    * Bank statements
    * Reconciliation process by partner

Creates a dashboard for accountants that includes:
--------------------------------------------------
    * List of Customer Invoices to Approve
    * Company Analysis
    * Graph of Treasury

Processes like maintaining general ledgers are done through the defined Financial Journals (entry move line or grouping is maintained through a journal) 
for a particular financial year and for preparation of vouchers there is a module named account_voucher.
    """,
    'website': 'https://www.odoo.com/page/billing',
    'depends' : ['base_setup', 'product', 'analytic', 'board', 'edi', 'report'],
    'data': [
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'account_menuitem.xml',
        'report/account_invoice_report_view.xml',
        'report/account_entries_report_view.xml',
        'report/account_treasury_report_view.xml',
        'report/account_report_view.xml',
        'report/account_analytic_entries_report_view.xml',
        'wizard/account_move_bank_reconcile_view.xml',
        'wizard/account_use_model_view.xml',
        'account_installer.xml',
        'wizard/account_period_close_view.xml',
        'wizard/account_reconcile_view.xml',
        'wizard/account_unreconcile_view.xml',
        'wizard/account_statement_from_invoice_view.xml',
        'account_view.xml',
        'account_report.xml',
        'account_financial_report_data.xml',
        'wizard/account_report_common_view.xml',
        'wizard/account_invoice_refund_view.xml',
        'wizard/account_fiscalyear_close_state.xml',
        'wizard/account_chart_view.xml',
        'wizard/account_tax_chart_view.xml',
        'wizard/account_move_line_reconcile_select_view.xml',
        'wizard/account_open_closed_fiscalyear_view.xml',
        'wizard/account_move_line_unreconcile_select_view.xml',
        'wizard/account_vat_view.xml',
        'wizard/account_report_print_journal_view.xml',
        'wizard/account_report_general_journal_view.xml',
        'wizard/account_report_central_journal_view.xml',
        'wizard/account_subscription_generate_view.xml',
        'wizard/account_fiscalyear_close_view.xml',
        'wizard/account_state_open_view.xml',
        'wizard/account_journal_select_view.xml',
        'wizard/account_change_currency_view.xml',
        'wizard/account_validate_move_view.xml',
        'wizard/account_report_general_ledger_view.xml',
        'wizard/account_invoice_state_view.xml',
        'wizard/account_report_partner_balance_view.xml',
        'wizard/account_report_account_balance_view.xml',
        'wizard/account_report_aged_partner_balance_view.xml',
        'wizard/account_report_partner_ledger_view.xml',
        'wizard/account_reconcile_partner_process_view.xml',
        'wizard/account_automatic_reconcile_view.xml',
        'wizard/account_financial_report_view.xml',
        'wizard/pos_box.xml',
        'project/wizard/project_account_analytic_line_view.xml',
        'account_end_fy.xml',
        'account_invoice_view.xml',
        'data/account_data.xml',
        'data/data_account_type.xml',
        'data/configurable_account_chart.xml',
        'account_invoice_workflow.xml',
        'project/project_view.xml',
        'project/project_report.xml',
        'project/wizard/account_analytic_balance_report_view.xml',
        'project/wizard/account_analytic_cost_ledger_view.xml',
        'project/wizard/account_analytic_inverted_balance_report.xml',
        'project/wizard/account_analytic_journal_report_view.xml',
        'project/wizard/account_analytic_cost_ledger_for_journal_report_view.xml',
        'project/wizard/account_analytic_chart_view.xml',
        'partner_view.xml',
        'product_view.xml',
        'account_assert_test.xml',
        'ir_sequence_view.xml',
        'company_view.xml',
        'edi/invoice_action_data.xml',
        'account_bank_view.xml',
        'res_config_view.xml',
        'account_pre_install.yml',
        'views/report_vat.xml',
        'views/report_invoice.xml',
        'views/report_trialbalance.xml',
        'views/report_centraljournal.xml',
        'views/report_overdue.xml',
        'views/report_generaljournal.xml',
        'views/report_journal.xml',
        'views/report_salepurchasejournal.xml',
        'views/report_partnerbalance.xml',
        'views/report_agedpartnerbalance.xml',
        'views/report_partnerledger.xml',
        'views/report_partnerledgerother.xml',
        'views/report_financial.xml',
        'views/report_generalledger.xml',
        'project/views/report_analyticbalance.xml',
        'project/views/report_analyticjournal.xml',
        'project/views/report_analyticcostledgerquantity.xml',
        'project/views/report_analyticcostledger.xml',
        'project/views/report_invertedanalyticbalance.xml',
        'views/account.xml',
    ],
    'qweb' : [
        "static/src/xml/account_move_reconciliation.xml",
        "static/src/xml/account_move_line_quickadd.xml",
        "static/src/xml/account_bank_statement_reconciliation.xml",
    ],
    'demo': [
        'demo/account_demo.xml',
        'project/project_demo.xml',
        'project/analytic_account_demo.xml',
        'demo/account_minimal.xml',
        'demo/account_invoice_demo.xml',
        'demo/account_bank_statement.xml',
        'account_unit_test.xml',
    ],
    'test': [
        'test/account_test_users.yml',
        'test/account_customer_invoice.yml',
        'test/account_supplier_invoice.yml',
        'test/account_change_currency.yml',
        'test/chart_of_account.yml',
        'test/account_period_close.yml',
        'test/account_use_model.yml',
        'test/account_validate_account_move.yml',
        'test/test_edi_invoice.yml',
        'test/account_report.yml',
        'test/account_fiscalyear_close.yml', #last test, as it will definitively close the demo fiscalyear
    ],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
