{
    "name": "PoS Bancontact Pay & Wero",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Accept Bancontact Pay and Wero QR code payments in PoS (Payconiq)",
    "depends": ["pos_payment_method"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_bancontact_pay/static/src/payment_method_bancontact_pay.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
