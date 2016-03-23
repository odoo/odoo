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

Odoo has the capacity to manage lots and serial numbers ensuring compliance with the traceability requirements imposed by the majority of industries.

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
    'category': 'Inventory Management',
    'sequence': 13,
    'demo': [
        'data/stock_demo_pre.yml',
        'data/stock_demo.xml',
        'data/procurement_demo.xml',
        'data/stock_orderpoint_demo.xml',
        'data/stock_orderpoint_demo.yml',
        'data/stock_demo.yml',
        'data/stock_location_demo_cpu1.xml',
        'data/stock_location_demo_cpu3.yml',
    ],
    'data': [
        'security/stock_security.xml',
        'security/ir.model.access.csv',

        'views/stock_menu_views.xml',

        'report/report_stock_forecast.xml',
        'report/stock_report_views.xml',
        'report/report_stock_view.xml',
        'report/report_package_barcode.xml',
        'report/report_lot_barcode.xml',
        'report/report_location_barcode.xml',
        'report/report_stockpicking_operations.xml',
        'report/report_deliveryslip.xml',
        'report/report_stockinventory.xml',

        'wizard/stock_move_view.xml',
        'wizard/stock_change_product_qty_view.xml',
        'wizard/stock_return_picking_view.xml',
        'wizard/make_procurement_view.xml',
        'wizard/orderpoint_procurement_view.xml',
        'wizard/stock_immediate_transfer.xml',
        'wizard/stock_backorder_confirmation.xml',

        'views/res_partner_views.xml',
        'views/product_strategy_views.xml',
        'views/stock_inventory_views.xml',
        'stock_view.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_views.xml',
        'views/procurement_views.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_pack_operation_views.xml',
        'views/product_views.xml',
        'views/stock_config_settings_views.xml',

        'data/default_barcode_patterns.xml',
        'data/stock_data.xml',
        'data/stock_data.yml',
        'data/stock_incoterms_data.xml',
        'data/stock_sequence_data.xml',
        'data/web_planner_data.xml',
    ],
    'test': [
        'test/procrule.yml',
        'test/stock_users.yml',
        'test/packing.yml',
        'test/packingneg.yml',
        'test/wiseoperator.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
