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
    "name" : "Accounting and Financial Management",
    "version" : "1.1",
    "depends" : ["product", "analytic", "process"],
    "author" : "Tiny",
    "category": 'Generic Modules/Accounting',
    "description": """Financial and accounting module that covers:
    General accountings
    Cost / Analytic accounting
    Third party accounting
    Taxes management
    Budgets
    Customer and Supplier Invoices
    Bank statements

The processes like maintaining of general ledger is done through the defined financial Journals (entry move line or
grouping is maintained through journal) for a particular financial year and for preparation of vouchers there is a
module named account_voucherss
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        #'test/test_parent_structure.yml',
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'account_menuitem.xml',
        'wizard/account_invoice_refund_view.xml',
        'wizard/account_period_close_view.xml',
        'wizard/account_fiscalyear_close_state.xml',
        'wizard/account_chart_view.xml',
        'wizard/account_move_bank_reconcile_view.xml',
        'wizard/account_move_line_reconcile_select_view.xml',
        'wizard/account_move_journal_view.xml',
        'account_wizard.xml',
        'wizard/account_move_line_unreconcile_select_view.xml',
        'wizard/account_subscription_generate_view.xml',
        'project/wizard/project_account_analytic_line_view.xml',
        'account_view.xml',
        'account_end_fy.xml',
        'account_invoice_view.xml',
        'account_report.xml',
        'partner_view.xml',
        'data/account_invoice.xml',
        'data/account_data2.xml',
        'account_invoice_workflow.xml',
        'project/project_view.xml',
        'project/project_report.xml',
        'product_view.xml',
        'account_assert_test.xml',
        'process/statement_process.xml',
        'process/customer_invoice_process.xml',
        'process/supplier_invoice_process.xml',
        'sequence_view.xml',
        'company_view.xml',
        'account_installer.xml',
        'report/account_invoice_report_view.xml',
        'report/account_report_view.xml',
    ],
    'demo_xml': [
        #'demo/price_accuracy00.yml',
        'account_demo.xml',
        'project/project_demo.xml',
        'project/analytic_account_demo.xml',
        'demo/account_minimal.xml',
        'account_unit_test.xml',
    ],
    'installable': True,
    'active': False,
    'certificate': '0080331923549',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
