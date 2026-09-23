{
    "name": "Point of Sale - Coupons & Loyalty",
    "version": "2.0",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Use Coupons, Gift Cards and Loyalty programs in Point of Sale",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "loyalty",
        "point_of_sale",
    ],
    "data": [
        "security/ir.access.csv",
        "data/default_barcode_patterns.xml",
        "data/gift_card_data.xml",
        "views/loyalty_card_views.xml",
        "views/loyalty_mail_views.xml",
        "views/pos_loyalty_menu_views.xml",
        "views/res_config_settings_view.xml",
        "views/loyalty_program_views.xml",
        "views/res_partner_views.xml",
    ],
    "demo": [
        "demo/pos_loyalty_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "pos_loyalty/static/src/portal/*",
        ],
        "point_of_sale._assets_pos": [
            "pos_loyalty/static/src/**/*",
            (
                "remove",
                "pos_loyalty/static/src/portal/*",
            ),
        ],
        "web.assets_tests": [
            "pos_loyalty/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_loyalty/static/tests/unit/**/*",
        ],
    },
    "auto_install": True,
    "uninstall_hook": "uninstall_hook",
}
