{
    "name": "POS Self Order Bancontact Pay",
    "category": "Sales/Point of Sale",
    "sequence": 101,
    "summary": "Disable Bancontact Pay payment methods for the kiosk",
    "auto_install": True,
    "depends": ["pos_self_order", "pos_bancontact_pay"],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_self_order_bancontact_pay/static/src/app/payment_bancontact.js",
        ],
        "pos_self_order.assets": [
            "pos_self_order_bancontact_pay/static/src/app/payment_page.js",
        ],
        "pos_self_order.assets_tests": [
            "pos_bancontact_pay/static/tests/tours/utils/*",
            "pos_self_order_bancontact_pay/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_self_order_bancontact_pay/static/tests/unit/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
