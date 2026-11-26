{
    'name': 'POS Worldline',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Worldline Terminal API compatible payment terminal',
    'data': [
        'security/ir.access.csv',
        'views/pos_payment_method_views.xml',
        'wizard/pos_worldline_terminal_wizard_views.xml',
    ],
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_worldline/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_worldline/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
