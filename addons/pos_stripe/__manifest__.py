# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Stripe',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Stripe payment terminal',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale', 'payment_stripe'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_stripe/static/src/**/*',
        ],
        'point_of_sale.payment_terminals': [
            'pos_stripe/static/src/app/payment_stripe.js',
        ],
        'web.assets_unit_tests': [
            'pos_stripe/static/tests/unit/data/**/*'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
