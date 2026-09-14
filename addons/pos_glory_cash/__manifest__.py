{
    "name": "POS Glory Cash Machines",
    "version": "1.1",
    "category": "Sales/Point of Sale",
    "summary": "Integrate your POS with a Glory automatic cash payment device",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pos_glory_cash/static/src/**/*",
            (
                "remove",
                "pos_glory_cash/static/src/app/**/*",
            ),
        ],
        "point_of_sale._assets_pos": [
            "pos_glory_cash/static/src/**/*",
            (
                "remove",
                "pos_glory_cash/static/src/backend/**/*",
            ),
        ],
        "web.assets_unit_tests": [
            "pos_glory_cash/static/tests/**/*",
            "pos_glory_cash/static/src/glory_service.js",
            "pos_glory_cash/static/src/backend/**/*",
            "pos_glory_cash/static/src/utils/*.js",
        ],
    },
}
