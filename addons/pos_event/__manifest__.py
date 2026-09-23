{
    "name": "POS - Event",
    "version": "1.0",
    "category": "Hidden",
    "summary": "Link module between Point of Sale and Event",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "event_product",
    ],
    "data": [
        "security/ir.access.csv",
        "data/point_of_sale_data.xml",
        "data/event_product_data.xml",
        "views/event_registration_views.xml",
        "views/event_event_views.xml",
        "views/pos_order_views.xml",
    ],
    "demo": [
        "demo/event_product_demo.xml",
        "demo/point_of_sale_demo.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_event/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_event/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_event/static/tests/unit/**/*",
        ],
    },
    "auto_install": True,
}
