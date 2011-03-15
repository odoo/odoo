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
    "name": "Payment Management",
    "version": "1.1",
    "author": "OpenERP SA",
    "category": "Generic Modules/Payment",
    "description": """
This module provides :
----------------------
* a more efficient way to manage invoice payment.
* a basic mechanism to easily plug various automated payment.
    """,
    'images': ['images/payment_mode.jpeg','images/payment_order.jpeg'],
    'depends': ['account','account_voucher'],
    'init_xml': [],
    'update_xml': [
        'security/account_payment_security.xml',
        'security/ir.model.access.csv',
        'wizard/account_payment_pay_view.xml',
        'wizard/account_payment_populate_statement_view.xml',
        'wizard/account_payment_create_order_view.xml',
        'account_payment_view.xml',
        'account_payment_workflow.xml',
        'account_payment_sequence.xml',
        'account_invoice_view.xml',
        'account_payment_report.xml',
    ],
    'demo_xml': ['account_payment_demo.xml'],
    'test': [
             'test/account_payment.yml',
             'test/account_payment_report.yml'
    ],
    'installable': True,
    'active': False,
    'certificate': '0061703998541',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
