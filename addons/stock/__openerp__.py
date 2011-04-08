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
    "name" : "Inventory Management",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "description" : """
OpenERP Inventory Management module can manage multi-warehouses, multi and structured stock locations.
======================================================================================================

Thanks to the double entry management, the inventory controlling is powerful and flexible:
    * Moves history and planning,
    * Different inventory methods (FIFO, LIFO, ...)
    * Stock valuation (standard or average price, ...)
    * Robustness faced with Inventory differences
    * Automatic reordering rules (stock level, JIT, ...)
    * Bar code supported
    * Rapid detection of mistakes through double entry system
    * Traceability (upstream/downstream, production lots, serial number, ...)
    * Dashboard for warehouse that includes:
        * Procurement in exception
        * List of Incoming Products
        * List of Outgoing Products
        * Graph : Products to receive in delay (date < = today)
        * Graph : Products to send in delay (date < = today)
    """,
    "website" : "http://www.openerp.com",
    "images" : ["images/stock_forecast_report.png", "images/delivery_orders.jpeg", "images/inventory_analysis.jpeg","images/location.jpeg","images/moves_analysis.jpeg","images/physical_inventories.jpeg","images/warehouse_dashboard.jpeg"],
    "depends" : ["product", "account"],
    "category" : "Warehouse",
    "init_xml" : [],
    "demo_xml" : ["stock_demo.xml"],
    "update_xml" : [
        "security/stock_security.xml",
        "security/ir.model.access.csv",
        "stock_data.xml",
        "wizard/stock_move_view.xml",
        "wizard/stock_change_product_qty_view.xml",
        "wizard/stock_partial_picking_view.xml",
        "wizard/stock_partial_move_view.xml",
        "wizard/stock_fill_inventory_view.xml",
        "wizard/stock_invoice_onshipping_view.xml",
        "wizard/stock_inventory_merge_view.xml",
        "wizard/stock_location_product_view.xml",
        "wizard/stock_splitinto_view.xml",
        "wizard/stock_inventory_line_split_view.xml",
        "wizard/stock_change_standard_price_view.xml",
        'wizard/stock_return_picking_view.xml',
        "stock_workflow.xml",
        "stock_incoterms.xml",
        "stock_view.xml",
        "stock_report.xml",
        "stock_sequence.xml",
        "product_data.xml",
        "product_view.xml",
        "partner_view.xml",
        "report/report_stock_move_view.xml",
        "report/report_stock_view.xml",
        "board_warehouse_view.xml"
    ],
    'test': ['test/stock_test.yml',
             'test/stock_report.yml',
             ],
    'installable': True,
    'active': False,
    'certificate': '0055421559965',
}
