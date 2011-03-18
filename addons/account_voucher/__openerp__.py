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
    "name" : "Accounting Voucher Entries",
    "version" : "1.0",
    "author" : 'OpenERP SA',
    "description": """
    Account Voucher module includes all the basic requirements of Voucher Entries for Bank, Cash, Sales, Purchase, Expanse, Contra, etc.
    ====================================================================================================================================
    * Voucher Entry
    * Voucher Receipt
    * Cheque Register
    """,
    "category" : "Finance",
    "website" : "http://tinyerp.com",
    "images" : ["images/customer_payment.jpeg","images/journal_voucher.jpeg","images/sales_receipt.jpeg","images/supplier_voucher.jpeg"],
    "depends" : ["account"],
    "init_xml" : [],

    "demo_xml" : [],

    "update_xml" : [
        "security/ir.model.access.csv",
        "account_voucher_sequence.xml",
        "account_voucher_workflow.xml",
        "account_voucher_report.xml",
        "wizard/account_voucher_unreconcile_view.xml",
        "wizard/account_statement_from_invoice_view.xml",
        "account_voucher_view.xml",
        "voucher_payment_receipt_view.xml",
        "voucher_sales_purchase_view.xml",
        "account_voucher_wizard.xml",
        "account_voucher_pay_invoice.xml",
        "report/account_voucher_sales_receipt_view.xml",
        "security/account_voucher_security.xml"
    ],
    "test" : [
        "test/account_voucher.yml",
        "test/sales_receipt.yml",
        "test/sales_payment.yml",
        "test/account_voucher_report.yml"
    ],
    'certificate': '0037580727101',
    "active": False,
    "installable": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
