# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Order Codes',
    'category': 'Sales/Point of Sale',
    'summary': 'Require a one-time 5-digit code to validate a Point of Sale or kiosk order',
    'description': """
Ask the customer for a single-use 5-digit code before an order is validated.

The code is checked against the "Order Codes" model: an unknown or already used
code is rejected in place (the boxes turn red and shake), a valid one is consumed
and the order goes through. The kiosk only offers the code popup, while the Point
of Sale also offers a "Force Validate" button for the cashier.
""",
    'depends': ['point_of_sale', 'pos_self_order'],
    'data': [
        'security/ir.access.csv',
        'views/pos_unique_code_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_unique_code/static/src/app/**/*',
            'pos_unique_code/static/src/pos/**/*',
        ],
        'pos_self_order.assets': [
            'pos_unique_code/static/src/app/**/*',
            'pos_unique_code/static/src/self_order/**/*',
        ],
        'web.assets_tests': [
            'pos_unique_code/static/tests/helpers/**/*',
            'pos_unique_code/static/tests/tours/**/*',
        ],
        'pos_self_order.assets_tests': [
            'pos_unique_code/static/tests/helpers/**/*',
            'pos_unique_code/static/tests/kiosk_tours/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
