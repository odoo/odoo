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
    'name': 'Sales Management',
    'version': '1.0',
    'category': 'Sales Management',
    "sequence": 14,
    'complexity': "easy",
    'description': """
The base module to manage quotations and sales orders.
======================================================

Workflow with validation steps:
-------------------------------
    * Quotation -> Sales order -> Invoice

Invoicing methods:
------------------
    * Invoice on order (before or after shipping)
    * Invoice on delivery
    * Invoice on timesheets
    * Advance invoice

Partners preferences:
---------------------
    * shipping
    * invoicing
    * incoterm

Products stocks and prices
--------------------------

Delivery methods:
-----------------
    * all at once
    * multi-parcel
    * delivery costs

Dashboard for Sales Manager that includes:
------------------------------------------
    * Quotations
    * Sales by Month
    * Graph of Sales by Salesman in last 90 days
    * Graph of Sales per Customer in last 90 days
    * Graph of Sales by Product's Category in last 90 days
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/deliveries_to_invoice.jpeg','images/sale_dashboard.jpeg','images/Sale_order_line_to_invoice.jpeg','images/sale_order.jpeg','images/sales_analysis.jpeg'],
    'depends': ['stock', 'procurement', 'board', 'account_voucher'],
    'init_xml': [],
    'update_xml': [
        'wizard/sale_make_invoice_advance.xml',
        'wizard/sale_line_invoice.xml',
        'wizard/sale_make_invoice.xml',
        'security/sale_security.xml',
        'security/ir.model.access.csv',
        'company_view.xml',
        'sale_workflow.xml',
        'sale_sequence.xml',
        'sale_report.xml',
        'sale_data.xml',
        'sale_view.xml',
        'report/sale_report_view.xml',
        'stock_view.xml',
        'process/sale_process.xml',
        'board_sale_view.xml',
        'edi/sale_order_action_data.xml',
        'res_config_view.xml',
    ],
    'demo_xml': ['sale_demo.xml'],
    'test': [
        'test/sale_order_demo.yml',
        'test/picking_order_policy.yml',
        'test/manual_order_policy.yml',
        'test/postpaid_order_policy.yml',
        'test/prepaid_order_policy.yml',
        'test/cancel_order.yml',
        'test/delete_order.yml',
        'test/edi_sale_order.yml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'certificate': '0058103601429',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
