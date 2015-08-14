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
    'name': 'Warehouse Management',
    'version': '1.1',
    'author': 'OpenERP SA',
    'summary': 'Inventory, Logistic, Storage',
    'description': """
Manage multi-warehouses, multi- and structured stock locations
==============================================================

The warehouse and inventory management is based on a hierarchical location structure, from warehouses to storage bins.
The double entry inventory system allows you to manage customers, suppliers as well as manufacturing inventories.

OpenERP has the capacity to manage lots and serial numbers ensuring compliance with the traceability requirements imposed by the majority of industries.

Key Features
------------
* Moves history and planning,
* Minimum stock rules
* Support for barcodes
* Rapid detection of mistakes through double entry system
* Traceability (Serial Numbers, Packages, ...)

Dashboard / Reports for Warehouse Management will include:
----------------------------------------------------------
* Incoming Products (Graph)
* Outgoing Products (Graph)
* Procurement in Exception
* Inventory Analysis
* Last Product Inventories
* Moves Analysis
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['product', 'procurement', 'board', 'web_kanban_gauge', 'web_kanban_sparkline'],
    'category': 'Warehouse Management',
    'sequence': 16,
    'demo': [
        'stock_demo_pre.yml',
        'stock_demo.xml',
        'procurement_demo.xml',
        'stock_orderpoint.xml',
        'stock_orderpoint.yml',
        'stock_demo.yml',
        'stock_location_demo_cpu1.xml',
        'stock_location_demo_cpu3.yml',
    ],
    'data': [
        'security/stock_security.xml',
        'security/ir.model.access.csv',
        'stock_data.xml',
        'stock_data.yml',
        'wizard/stock_move_view.xml',
        'wizard/stock_change_product_qty_view.xml',
        'wizard/stock_return_picking_view.xml',
        'wizard/make_procurement_view.xml',
        'wizard/orderpoint_procurement_view.xml',
        'wizard/stock_transfer_details.xml',
        'stock_incoterms.xml',
        'stock_report.xml',
        'stock_view.xml',
        'stock_sequence.xml',
        'product_view.xml',
        'partner_view.xml',
        'report/report_stock_view.xml',
        'res_config_view.xml',
        'views/report_package_barcode.xml',
        'views/report_lot_barcode.xml',
        'views/report_location_barcode.xml',
        'views/report_stockpicking.xml',
        'views/report_stockinventory.xml',
        'views/stock.xml',
    ],
    'test': [
        'test/inventory.yml',
        'test/move.yml',
        'test/procrule.yml',
        'test/stock_users.yml',
        'stock_demo.yml',
        'test/shipment.yml',
        'test/packing.yml',
        'test/packingneg.yml',
        'test/wiseoperator.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': ['static/src/xml/picking.xml'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
