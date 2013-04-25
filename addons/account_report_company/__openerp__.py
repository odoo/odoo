# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013 OpenERP S.A. <http://openerp.com>
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
    'name': 'Invoice Analysis per Company',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
Add an extra Company dimension on Invoices for consolidated Invoice Analysis
============================================================================

By default Customer and Supplier invoices can be linked to a contact within
a company, but the company is not a direct reference in the database structure for
invoices. Journal Entries are however always linked to the company and not to
contacts, so that Accounts Payable and Receivable are always correct and consolidated
at company level.

When many different contacts/departments need to be invoiced within the same parent company,
this can make reporting by Company more difficult: reports are directly based on the
database structure and would not provide an aggregated company dimension.

This modules solves the problem by adding an explicit company reference on invoices,
automatically computed from the invoice contact, and use this new dimension
when grouping the list of Invoices or the Invoice Analysis report by Partner. 

Note: this module will likely be removed for the next major OpenERP version and
directly integrated in the core accounting. 
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['account'],
    'data': [
        'account_invoice_view.xml',
        'res_partner_view.xml',
        'report/account_invoice_report_view.xml',
    ],
    'auto_install': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
