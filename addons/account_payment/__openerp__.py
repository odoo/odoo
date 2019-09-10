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
    'name': 'Suppliers Payment Management',
    'version': '1.1',
    'author': 'OpenERP SA',
    'category': 'Accounting & Finance',
    'description': """
Module to manage the payment of your supplier invoices.
=======================================================

This module allows you to create and manage your payment orders, with purposes to
--------------------------------------------------------------------------------- 
    * serve as base for an easy plug-in of various automated payment mechanisms.
    * provide a more efficient way to manage invoice payment.

Warning:
~~~~~~~~
The confirmation of a payment order does _not_ create accounting entries, it just 
records the fact that you gave your payment order to your bank. The booking of 
your order must be encoded as usual through a bank statement. Indeed, it's only 
when you get the confirmation from your bank that your order has been accepted 
that you can book it in your accounting. To help you with that operation, you 
have a new option to import payment orders as bank statement lines.
    """,
    'depends': ['account','account_voucher'],
    'data': [
        'security/account_payment_security.xml',
        'security/ir.model.access.csv',
        'wizard/account_payment_pay_view.xml',
        'wizard/account_payment_populate_statement_view.xml',
        'wizard/account_payment_create_order_view.xml',
        'account_payment_view.xml',
        'account_payment_workflow.xml',
        'account_payment_sequence.xml',
        'account_payment_report.xml',

        'views/report_paymentorder.xml',
    ],
    'demo': ['account_payment_demo.xml'],
    'test': [
        'test/account_payment_demo.yml',
        'test/cancel_payment_order.yml',
        'test/payment_order_process.yml',
        'test/account_payment_report.yml',
    ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
