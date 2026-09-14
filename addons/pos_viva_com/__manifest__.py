{
    "name": "PoS Viva.com",
    "version": "1.1",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Integrate your PoS with a Viva.com payment terminal",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "integration",
    ],
    "data": [
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_viva_com/static/src/**/*",
        ],
        "web.assets_tests": [
            "pos_viva_com/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_viva_com/static/tests/unit/data/**/*",
        ],
    },
}
