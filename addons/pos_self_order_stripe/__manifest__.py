# -*- coding: utf-8 -*-
{
    "name": "POS Self Order Stripe",
    "summary": "Addon for the Self Order App that allows customers to pay by Stripe.",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_stripe", "pos_self_order"],
    "auto_install": True,
    'data': [
        'views/assets_stripe.xml',
    ],
    'assets': {
        'pos_self_order.assets': [
            'pos_self_order_stripe/static/**/*',
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
