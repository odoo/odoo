# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Repairs',
    'sequence': 230,
    'category': 'Supply Chain/Inventory',
    'summary': 'Repair damaged products',
    'description': """
The aim is to have a complete module to manage all products repairs.
====================================================================

The following topics are covered by this module:
------------------------------------------------------
    * Add/remove products in the reparation
    * Impact for stocks
    * Warranty concept
    * Repair quotation report
    * Notes for the technician and for the final customer
""",
    'depends': ['sale_stock', 'sale_management'],
    'data': [
        'views/product_views.xml',
        'views/stock_move_views.xml',
        'views/repair_views.xml',
        'views/sale_order_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse_views.xml',
        'views/account_move_views.xml',
        'report/repair_reports.xml',
        'report/repair_templates_repair_order.xml',
        'data/repair_data.xml',
        'security/ir.access.csv',
    ],
    'demo': ['data/repair_demo.xml'],
    'post_init_hook': '_create_warehouse_data',
    'application': True,
    'assets': {
        'web.assets_backend': [
            'repair/static/src/**/*',
        ],
        'web.assets_tests': [
            'repair/static/tests/tours/*.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
