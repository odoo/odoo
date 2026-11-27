{
    "name": "PoS Bank QR payments",
    "category": "Sales/Point of Sale",
    "sequence": 7,
    "summary": "Generate QR codes linked to your Bank for POS payments",
    "depends": ["pos_payment_method", "account"],
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_bank_qr/static/src/payment_method_bank_qr.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
