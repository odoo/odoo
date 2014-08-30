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
    'name' : 'Online Billing',
    'version' : '1.0',
    'author' : 'OpenERP SA',
    'summary': 'Send Invoices and Track Payments',
    'description': """
Invoicing & Payments by Accounting Voucher & Receipts
=====================================================
The specific and easy-to-use Invoicing system in OpenERP allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your suppliers and customers. 

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. 

The Invoicing system includes receipts and vouchers (an easy way to keep track of sales and purchases). It also offers you an easy method of registering payments, without having to encode complete abstracts of account.

This module manages:

* Voucher Entry
* Voucher Receipt [Sales & Purchase]
* Voucher Payment [Customer & Supplier]
    """,
    'category': 'Accounting & Finance',
    'sequence': 4,
    'website' : 'https://www.odoo.com/page/billing',
    'images' : ['images/customer_payment.jpeg','images/journal_voucher.jpeg','images/sales_receipt.jpeg','images/supplier_voucher.jpeg','images/customer_invoice.jpeg','images/customer_refunds.jpeg'],
    'depends' : ['account'],
    'demo' : [],
    'data' : [
        'security/ir.model.access.csv',
        'account_voucher_sequence.xml',
        'account_voucher_workflow.xml',
        'account_voucher_view.xml',
        'voucher_payment_receipt_view.xml',
        'voucher_sales_purchase_view.xml',
        'account_voucher_wizard.xml',
        'account_voucher_pay_invoice.xml',
        'report/account_voucher_sales_receipt_view.xml',
        'security/account_voucher_security.xml',
        'account_voucher_data.xml',
    ],
    'test' : [
        'test/account_voucher_users.yml',
        'test/case5_suppl_usd_usd.yml',
        'test/account_voucher.yml',
        'test/sales_receipt.yml',
        'test/sales_payment.yml',
        'test/case1_usd_usd.yml',
        'test/case1_usd_usd_payment_rate.yml',
        'test/case2_usd_eur_debtor_in_eur.yml',
        'test/case2_usd_eur_debtor_in_usd.yml',
        'test/case3_eur_eur.yml',
        'test/case4_cad_chf.yml',
        'test/case_eur_usd.yml',
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
