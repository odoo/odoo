# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "POS Self Order QRIS",
    "category": "Sales/Point of Sale",
    "sequence": 101,
    "summary": "Accept QRIS QR code payments in a kiosk.",
    "depends": ["pos_self_order", "l10n_id_pos"],
    "auto_install": True,
    "assets": {
        "pos_self_order.assets": [
            "point_of_sale/static/lib/qrcode.js",
            "pos_self_order_qris/static/src/payment/payment_qris.js",
            "pos_self_order_qris/static/src/payment/payment_page.js",
            "pos_self_order_qris/static/src/payment/payment_page.xml",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
