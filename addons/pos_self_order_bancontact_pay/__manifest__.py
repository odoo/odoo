{
    "name": "POS Self Order Bancontact Pay & Wero",
    "category": "Sales/Point of Sale",
    "sequence": 101,
    "summary": "Accept Bancontact Pay and Wero QR code payments in a kiosk (Payconiq).",
    "auto_install": True,
    "depends": ["pos_self_order", "pos_bancontact_pay"],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_self_order_bancontact_pay/static/src/app/bancontact_pay/**/*",
        ],
        "pos_self_order.assets": [
            "pos_self_order_bancontact_pay/static/src/app/self_order/**/*",
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
