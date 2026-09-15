{
    "name": "PoS DPO Pay",
    "version": "1.1",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Integrate your POS with DPO payment terminal.",
    "description": """
Allow DPO POS payments
==============================

It supports all currencies supported by the terminal device — primarily for use in the **African region**.
It enables customers to pay for their orders using debit/credit cards and Mobile Money through DPO POS terminals.
A DPO merchant account is required to process transactions.
Features include:

* Quick payments by swiping, scanning, or tapping your credit/debit card or Mobile Money (Airtel Money / M-Pesa) at the payment terminal.
* Supported cards: Visa, MasterCard, American Express etc.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "integration",
    ],
    "data": [
        "views/pos_payment_method_views.xml",
        "views/pos_payment_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_dpopay/static/src/**/*",
        ],
    },
}
