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
    'name': 'Sale To Stock',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This Module manage quotations and sales orders. 
===========================================================================

Workflow with validation steps:
-------------------------------
    * Quotation -> Sales order -> Invoice

Create Invoice:
---------------
    * Invoice on Demand
    * Invoice on Delivery Order
    * Invoice Before Delivery

Partners preferences:
---------------------
    * Incoterm
    * Shipping
    * Invoicing

Products stocks and prices:
--------------------------

Delivery method:
-----------------
    * The Poste
    * Free Delivery Charges
    * Normal Delivery Charges
    * Based on the Delivery Order(if not Add to sale order) 

Dashboard for Sales Manager that includes:
------------------------------------------
    * My Quotations
    * Monthly Turnover (Graph)
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': [],
    'depends': ['sale', 'procurement'],
    'init_xml': [],
    'update_xml': ['wizard/sale_make_invoice_advance.xml',
                   'wizard/sale_make_invoice.xml',
                   'security/sale_stock_security.xml',
                   'security/ir.model.access.csv',
                   'company_view.xml',
                   'sale_stock_view.xml',
                   'sale_stock_workflow.xml',
                    'res_config_view.xml',
                    'report/sale_report_view.xml',
                    'process/sale_stock_process.xml',
                   ],
   'data': ['sale_stock_data.xml'],
   'demo_xml': ['sale_stock_demo.xml'],
    'test': ['test/cancel_order_sale_stock.yml',
             'test/picking_order_policy.yml',
             'test/manual_order_policy.yml'
             ],
    'installable': True,
    'auto_install': True,
    
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: