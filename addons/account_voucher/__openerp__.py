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
    'name' : 'Sale & Purchase Vouchers',
    'version' : '1.0',
    'author' : 'OpenERP SA',
    'summary': 'Manage your debts and credits thanks to simple sale/purchase receipts',
    'description': """
TODO

old description:
Invoicing & Payments by Accounting Voucher & Receipts
=====================================================
The specific and easy-to-use Invoicing system in Odoo allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your suppliers and customers. 

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. 

The Invoicing system includes receipts and vouchers (an easy way to keep track of sales and purchases). It also offers you an easy method of registering payments, without having to encode complete abstracts of account.

This module manages:

* Voucher Entry
* Voucher Receipt [Sales & Purchase]
* Voucher Payment [Customer & Supplier]
    """,
    'category': 'Accounting & Finance',
    'sequence': 20,
    'website' : 'https://www.odoo.com/page/billing',
    'depends' : ['account'],
    'demo' : [],
    'data' : [
        'security/ir.model.access.csv',
        'account_voucher_view.xml',
        'voucher_sales_purchase_view.xml',
        'security/account_voucher_security.xml',
        'account_voucher_data.xml',
    ],
    'test' : [
        'test/account_voucher_users.yml',
        'test/account_voucher_chart.yml',
        'test/account_voucher.yml',
        'test/sales_receipt.yml',
    ],
    'auto_install': False,
    'installable': True,
}
