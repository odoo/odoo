# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "POS Paymob",
    "version": "1.0",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Integrate your POS with a Paymob payment terminal",
    "data": [
        "views/pos_payment_method_views.xml",
    ],
    "depends": ["point_of_sale"],
    "installable": True,
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_paymob/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_paymob/static/tests/unit/data/**/*",
        ],
        "web.assets_tests": [
            "pos_paymob/static/tests/tours/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
