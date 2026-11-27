{
    "name": "POS Bancontact Pay bridge",
    "category": "Sales/Point of Sale",
    "sequence": 100,
    "summary": "Additional integrations for Bancontact Pay in the PoS.",
    "depends": ["point_of_sale", "pos_payment_method_bancontact_pay"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_bancontact_pay/static/src/app/**/*",
        ],
        'point_of_sale.customer_display_assets': [
            "pos_bancontact_pay/static/src/customer_display/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_bancontact_pay/static/tests/unit/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
