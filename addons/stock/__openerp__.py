# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Inventory Management',
    'version': '1.1',
    'summary': 'Inventory, Logistics, Warehousing',
    'description': """
Manage multi-warehouses, multi- and structured stock locations
==============================================================

The warehouse and inventory management is based on a hierarchical location structure, from warehouses to storage bins.
The double entry inventory system allows you to manage customers, vendors as well as manufacturing inventories.

OpenERP has the capacity to manage lots and serial numbers ensuring compliance with the traceability requirements imposed by the majority of industries.

Key Features
------------
* Moves history and planning,
* Minimum stock rules
* Support for barcodes
* Rapid detection of mistakes through double entry system
* Traceability (Serial Numbers, Packages, ...)

Dashboard / Reports for Inventory Management will include:
----------------------------------------------------------
* Incoming Products (Graph)
* Outgoing Products (Graph)
* Procurement in Exception
* Inventory Analysis
* Last Product Inventories
* Moves Analysis
    """,
    'website': 'https://www.odoo.com/page/warehouse',
    'depends': ['product', 'procurement', 'barcodes', 'web_planner'],
    'category': 'Warehouse',
    'sequence': 13,
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
        'data/default_barcode_patterns.xml',
        'security/stock_security.xml',
        'security/ir.model.access.csv',
        'stock_data.xml',
        'stock_data.yml',
        'wizard/stock_move_view.xml',
        'wizard/stock_change_product_qty_view.xml',
        'wizard/stock_return_picking_view.xml',
        'wizard/make_procurement_view.xml',
        'wizard/orderpoint_procurement_view.xml',
        'report/report_stock_forecast.xml',
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
        'views/report_stockpicking_operations.xml',
        'views/report_deliveryslip.xml',
        'views/report_stockinventory.xml',
        'stock_dashboard.xml',
        'wizard/stock_immediate_transfer.xml',
        'wizard/stock_backorder_confirmation.xml',
        'data/web_planner_data.xml',
    ],
    'test': [
        'test/inventory.yml',
        'test/move.yml',
        'test/procrule.yml',
        'test/stock_users.yml',
        'test/shipment.yml',
        'test/packing.yml',
        'test/packingneg.yml',
        'test/wiseoperator.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
