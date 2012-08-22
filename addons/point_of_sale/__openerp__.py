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
This module provides a quick and easy sale process.
===================================================

Main features:
--------------
    * Fast encoding of the sale
    * Allow to choose one payment mode (the quick way) or to split the payment between several payment mode
    * Computation of the amount of money to return
    * Create and confirm picking list automatically
    * Allow the user to create invoice automatically
    * Allow to refund former sales
    """,
    'author': 'OpenERP SA',
    'images': ['images/cash_registers.jpeg', 'images/pos_analysis.jpeg','images/register_analysis.jpeg','images/sale_order_pos.jpeg','images/product_pos.jpeg'],
    'depends': ['sale'],
    'data': [
        'security/point_of_sale_security.xml',
        'security/ir.model.access.csv',
        'wizard/pos_details.xml',
        'wizard/pos_confirm.xml',
        'wizard/pos_discount.xml',
        'wizard/pos_open_statement.xml',
        'wizard/pos_payment_report_user_view.xml',
        'wizard/pos_sales_user.xml',
        'wizard/pos_receipt_view.xml',
        'wizard/pos_payment_report_user.xml',
        'wizard/pos_payment_report.xml',
        'wizard/pos_payment.xml',
        'wizard/pos_box.xml',
        'wizard/pos_session_opening.xml',
        'point_of_sale_report.xml',
        'point_of_sale_view.xml',
        'point_of_sale_data.xml',
        'report/pos_order_report_view.xml',
        'point_of_sale_sequence.xml',
        'point_of_sale_workflow.xml',
        'account_statement_view.xml',
        'account_statement_report.xml',
        'res_users_view.xml',
    ],
    'demo': [
        'point_of_sale_demo.xml',
        'account_statement_demo.xml',
        'test/00_register_open.yml'
    ],
    'test': [
        'test/01_order_to_payment.yml',
        'test/02_order_to_invoice.yml',
        'test/point_of_sale_report.yml'
    ],
    'installable': True,
    'application': True,
    # Web client
    'js': [
        'static/lib/backbone/backbone-0.9.2.js', 
        'static/lib/mousewheel/jquery.mousewheel-3.0.6.js',
        'static/src/js/pos_models.js',
        'static/src/js/pos_basewidget.js',
        'static/src/js/pos_keyboard_widget.js',
        'static/src/js/pos_scrollbar_widget.js',
        'static/src/js/pos_widgets.js',
        'static/src/js/pos_devices.js',
        'static/src/js/pos_screens.js',
        'static/src/js/pos_main.js'
    ],
    'css': [
        'static/src/css/pos.css',
        'static/src/css/keyboard.css'
    ],
    'qweb': ['static/src/xml/pos.xml'],
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
