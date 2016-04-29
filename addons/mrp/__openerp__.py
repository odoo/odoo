# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'MRP',
    'version': '1.1',
    'website': 'https://www.odoo.com/page/manufacturing',
    'category': 'Manufacturing',
    'sequence': 14,
    'summary': 'Manufacturing Orders, Bill of Materials, Routings',
    'depends': ['product', 'procurement', 'stock_account', 'resource', 'report'],
    'description': """
Manage the Manufacturing process in Odoo
===========================================

The manufacturing module allows you to cover planning, ordering, stocks and the manufacturing or assembly of products from raw materials and components. It handles the consumption and production of products according to a bill of materials and the necessary operations on machinery, tools or human resources according to routings.

It supports complete integration and planification of stockable goods, consumables or services. Services are completely integrated with the rest of the software. For instance, you can set up a sub-contracting service in a bill of materials to automatically purchase on order the assembly of your production.

Key Features
------------
* Make to Stock/Make to Order
* Multi-level bill of materials, no limit
* Multi-level routing, no limit
* Routings and work center integrated with analytic accounting
* Periodical scheduler computation 
* Allows to browse bills of materials in a complete structure that includes child and phantom bills of materials

Dashboard / Reports for MRP will include:
-----------------------------------------
* Procurements in Exception (Graph)
* Stock Value Variation (Graph)
* Work Order Analysis
    """,
    'data': [
        'security/mrp_security.xml',
        'security/ir.model.access.csv',
        'data/mrp_data_workflow.xml',
        'data/mrp_data.xml',
        'wizard/mrp_product_produce_views.xml',
        'wizard/change_production_qty_views.xml',
        'wizard/stock_move_consume_views.xml',
        'views/mrp_views_menus.xml',
        'views/mrp_property_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/mrp_routing_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_bom_views.xml',
        'views/procurement_views.xml',
        'views/product_views.xml',
        'views/stock_warehouse_views.xml',
        'views/res_company_views.xml',
        'views/mrp_config_settings_views.xml',
        'report/mrp_report_views_main.xml',
        'report/mrp_report_views.xml',
        'report/mrp_production_templates.xml',
        'report/mrp_bom_templates.xml',
    ],
    'demo': ['data/mrp_demo.xml'],
    'test': [
        'test/bom_with_service_type_product.yml',
        'test/mrp_users.yml',
        'test/order_demo.yml',
        'test/order_process.yml',
        'test/cancel_order.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
