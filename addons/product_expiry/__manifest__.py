{
    "name": "Products Expiration Date",
    "version": "1.1",
    "category": "Supply Chain/Inventory",
    "description": """
Track different dates on products and production lots.
======================================================

Following dates can be tracked:
-------------------------------
    - end of life
    - best before date
    - removal date
    - alert date

Also implements the removal strategy First Expiry First Out (FEFO) widely used, for example, in food industries.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/stock_security.xml",
        "views/production_lot_views.xml",
        "views/product_category_views.xml",
        "views/product_template_views.xml",
        "views/res_config_settings_views.xml",
        "views/stock_move_views.xml",
        "views/stock_quant_views.xml",
        "wizards/confirm_expiry_view.xml",
        "reports/report_deliveryslip.xml",
        "reports/report_lot_barcode.xml",
        "data/product_expiry_data.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "product_expiry/static/tests/tours/*.js",
        ],
        "web.assets_backend": [
            "product_expiry/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "product_expiry/static/tests/*.test.js",
        ],
    },
    "post_init_hook": "_enable_tracking_numbers",
}
