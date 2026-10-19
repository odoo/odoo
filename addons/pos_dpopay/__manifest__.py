# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PoS DPO Pay',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with DPO payment terminal.',
    'description': """
Allow DPO POS payments
==============================

It supports all currencies supported by the terminal device — primarily for use in the **African region**.
It enables customers to pay for their orders using debit/credit cards and Mobile Money through DPO POS terminals.
A DPO merchant account is required to process transactions.
Features include:

* Quick payments by swiping, scanning, or tapping your credit/debit card or Mobile Money (Airtel Money / M-Pesa) at the payment terminal.
* Supported cards: Visa, MasterCard, American Express etc.
    """,
    'data': [
        'views/pos_payment_method_views.xml',
        'views/pos_payment_views.xml',
    ],
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_dpopay/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
