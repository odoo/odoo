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
    'name': 'WMS Accounting',
    'version': '1.1',
    'author': 'OpenERP SA',
    'summary': 'Inventory, Logistic, Valuation, Accounting',
    'description' : """
TODO
======================
TODO

Key Features
------------
* Stock Valuation (periodical or automatic)
* Invoice from Picking

Dashboard / Reports for Warehouse Management will include:
----------------------------------------------------------
* TODO
    """,
    'website': 'http://www.openerp.com',
    'images': [],
    'depends': ['stock', 'account'],
    'category': 'Hidden',
    'sequence': 16,
    'demo': [
#        'stock_demo.xml',
#        'procurement_demo.xml',
#        'stock_orderpoint.xml',
#        'stock_demo.yml',
    ],
    'data': [
#        'security/stock_security.xml',
#        'security/ir.model.access.csv',
#        'stock_data.xml',
#        'wizard/stock_move_view.xml',
#        'wizard/stock_change_product_qty_view.xml',
#        'wizard/stock_partial_picking_view.xml',
#        'wizard/stock_partial_move_view.xml',
#        'wizard/stock_fill_inventory_view.xml',
#        'wizard/stock_invoice_onshipping_view.xml',
#        'wizard/stock_inventory_merge_view.xml',
#        'wizard/stock_location_product_view.xml',
#        'wizard/stock_splitinto_view.xml',
#        'wizard/stock_inventory_line_split_view.xml',
#        'wizard/stock_change_standard_price_view.xml',
#        'wizard/stock_return_picking_view.xml',
#        'wizard/make_procurement_view.xml',
#        'wizard/mrp_procurement_view.xml',
#        'wizard/orderpoint_procurement_view.xml',
#        'stock_workflow.xml',
#        'stock_incoterms.xml',
#        'stock_report.xml',
#        'stock_view.xml',
#        'stock_sequence.xml',
#        'product_data.xml',
        'product_view.xml',
#        'partner_view.xml',
#        'report/report_stock_move_view.xml',
#        'report/report_stock_view.xml',
#        'board_warehouse_view.xml',
#        'res_config_view.xml',
    ],
    'test': [
#        'test/inventory.yml',
#        'test/move.yml',
#        'test/shipment.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
