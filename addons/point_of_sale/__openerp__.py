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
    'name': 'Point of Sale',
    'version': '1.0.1',
    'category': 'Point Of Sale',
    'sequence': 6,
    'summary': 'Touchscreen Interface for Shops',
    'description': """
Quick and Easy sale process
===========================

This module allows you to manage your shop sales very easily with a fully web based touchscreen interface.
It is compatible with all PC tablets and the iPad, offering multiple payment methods. 

Product selection can be done in several ways: 

* Using a barcode reader
* Browsing through categories of products or via a text search.

Main Features
-------------
* Fast encoding of the sale
* Choose one payment method (the quick way) or split the payment between several payment methods
* Computation of the amount of money to return
* Create and confirm the picking list automatically
* Allows the user to create an invoice automatically
* Refund previous sales
    """,
    'author': 'OpenERP SA',
    'depends': ['sale_stock'],
    'data': [
        'data/report_paperformat.xml',
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'wizard/pos_box.xml',
        'wizard/pos_confirm.xml',
        'wizard/pos_details.xml',
        'wizard/pos_discount.xml',
        'wizard/pos_open_statement.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_session_opening.xml',
        'views/templates.xml',
        'point_of_sale_report.xml',
        'point_of_sale_view.xml',
        'point_of_sale_sequence.xml',
        'point_of_sale_data.xml',
        'report/pos_order_report_view.xml',
        'point_of_sale_workflow.xml',
        'account_statement_view.xml',
        'account_statement_report.xml',
        'res_users_view.xml',
        'res_partner_view.xml',
        'views/report_statement.xml',
        'views/report_usersproduct.xml',
        'views/report_receipt.xml',
        'views/report_saleslines.xml',
        'views/report_detailsofsales.xml',
        'views/report_payment.xml',
        'views/report_sessionsummary.xml',
        'views/point_of_sale.xml',
    ],
    'demo': [
        'point_of_sale_demo.xml',
        'account_statement_demo.xml',
    ],
    'test': [
        'test/00_register_open.yml',
        'test/01_order_to_payment.yml',
        'test/02_order_to_invoice.yml',
        'test/point_of_sale_report.yml',
        'test/account_statement_reports.yml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/pos.xml'],
    'website': 'https://www.odoo.com/page/point-of-sale',
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
