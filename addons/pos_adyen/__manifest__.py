{
    "name": "POS Adyen",
    "version": "1.1",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Integrate your POS with an Adyen payment terminal",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "integration",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_adyen/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_adyen/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_adyen/static/tests/unit/data/**/*",
        ],
    },
}
