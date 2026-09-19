{
    "name": "Repairs",
    "version": "1.3",
    "category": "Supply Chain/Inventory",
    "sequence": 230,
    "summary": "Repair damaged products",
    "description": """
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
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "sale_stock",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/repair_security.xml",
        "wizards/stock_warn_insufficient_qty_views.xml",
        "views/product_views.xml",
        "views/stock_move_views.xml",
        "views/repair_views.xml",
        "views/sale_order_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_warehouse_views.xml",
        "reports/repair_reports.xml",
        "reports/repair_templates_repair_order.xml",
        "data/repair_data.xml",
        "views/repair_menus.xml",
    ],
    "demo": [
        "demo/repair_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "repair/static/src/**/*",
        ],
        "web.assets_tests": [
            "repair/static/tests/tours/*.js",
        ],
    },
    "application": True,
    "post_init_hook": "_create_warehouse_data",
}
