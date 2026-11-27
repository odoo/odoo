{
    "name": "PoS DPO Pay",
    "category": "Sales/Point of Sale",
    "sequence": 7,
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
    "data": [
        "views/electronic_payment_views.xml",
    ],
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale.payment_terminals": [
            "pos_payment_method_dpopay/static/src/payment_method_dpopay.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
