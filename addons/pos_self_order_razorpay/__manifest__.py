{
    "name": "POS Self Order Razorpay",
    "version": "1.0",
    "summary": "Addon for the Self Order App that allows customers to pay by Razorpay POS Terminal.",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_razorpay", "pos_self_order"],
    "auto_install": True,
    'assets': {
        'pos_self_order.assets': [
            'pos_self_order_razorpay/static/**/*',
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
