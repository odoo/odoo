# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    "name" : "Accounting and financial management",
    "version" : "1.1",
    "depends" : ["product", "base", "process"],
    "author" : "Tiny",
    "description": """Financial and accounting module that covers:
    General accounting
    Cost / Analytic accounting
    Third party accounting
    Taxes management
    Budgets
    Customer and Supplier Invoices
    Bank statements
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'account_menuitem.xml',
        'account_wizard.xml',
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
    ],
    'demo_xml': [
        'account_demo.xml',
        'project/project_demo.xml',
        'project/analytic_account_demo.xml',
        'demo/account_minimal.xml',
        'test/invoice_basic_test.xml',
        'test/invoice_bug452854_test.xml',
    ],
    'installable': True,
    'active': False,
    'certificate': '0080331923549',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
