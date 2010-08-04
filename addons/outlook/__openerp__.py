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
    "author" : "OpenERP SA",
    "category": 'Generic Modules/Accounting',
    "description": """Financial and accounting module that covers:
    General accountings
    Cost / Analytic accounting
    Third party accounting
    Taxes management
    Budgets
    Customer and Supplier Invoices
    Bank statements
    Reconciliation process by partner
    Creates a dashboards for accountants that includes:
    * List of uninvoiced quotations
    * Graph of aged receivables
    * Graph of aged incomes

The processes like maintaining of general ledger is done through the defined financial Journals (entry move line or
grouping is maintained through journal) for a particular financial year and for preparation of vouchers there is a
module named account_vouchers
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    "depends" : ["product", "analytic", "process","board"],
    'update_xml': [],
    'demo_xml': [],
    'test': [
#        'test/account_customer_invoice.yml',
#        'test/account_supplier_invoice.yml',
#        'test/account_change_currency.yml',
#        'test/chart_of_account.yml',
#        'test/account_period_close.yml',
#        'test/account_fiscalyear_close_state.yml',
#        #'test/account_invoice_state.yml',
#        'test/account_use_model.yml',
#        'test/account_validate_account_move.yml',
#        'test/account_fiscalyear_close.yml',
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
