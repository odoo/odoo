{
    "name": "Warehouse Management: Batch Transfer",
    "version": "1.2",
    "category": "Supply Chain/Inventory",
    "description": """
This module adds the batch transfer option in warehouse management
==================================================================
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.access.csv",
        "views/stock_picking_batch_views.xml",
        "views/stock_picking_type_views.xml",
        "views/stock_move_line_views.xml",
        "views/stock_picking_wave_views.xml",
        "views/stock_picking_views.xml",
        "wizards/stock_picking_to_batch_views.xml",
        "wizards/stock_add_to_wave_views.xml",
        "reports/stock_picking_batch_report_views.xml",
        "reports/report_picking_batch.xml",
        "views/stock_picking_batch_menus.xml",
    ],
    "demo": [
        "demo/stock_picking_batch_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "stock_picking_batch/static/src/js/stock_picking_many2many_field.js",
            "stock_picking_batch/static/src/scss/*.scss",
        ],
        "web.assets_tests": [
            "stock_picking_batch/static/tests/tours/**/*",
        ],
    },
}
