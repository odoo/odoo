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
        'data/data_account_type.xml',
        'data/account_data.xml',
        'views/account_menuitem.xml',
        'views/account_payment_view.xml',
        'wizard/account_reconcile_view.xml',
        'wizard/account_unreconcile_view.xml',
        'views/account_view.xml',
        'views/account_report.xml',
        'wizard/account_invoice_refund_view.xml',
        'wizard/account_move_reversal_view.xml',
        'wizard/account_validate_move_view.xml',
        'wizard/account_invoice_state_view.xml',
        'wizard/account_log_followup_note_view.xml',
        'wizard/pos_box.xml',
        'views/account_end_fy.xml',
        'views/account_invoice_view.xml',
        'data/invoice_action_data.xml',
        'views/account_invoice_workflow.xml',
        'views/partner_view.xml',
        'views/product_view.xml',
        'views/account_analytic_view.xml',
        'views/company_view.xml',
        'views/account_bank_view.xml',
        'views/res_config_view.xml',
        'views/account_tip_data.xml',
        'views/account.xml',
        'views/report_invoice.xml',
        'report/account_invoice_report_view.xml',
        'views/account_journal_dashboard_view.xml',
    ],
    'demo': [
        'demo/account_demo.xml',
    ],
    'qweb': [
        "static/src/xml/account_reconciliation.xml",
        "static/src/xml/account_payment.xml",
        "static/src/xml/account_report_backend.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
