{
    'name': 'POS Mollie',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Mollie payment terminal',
    'depends': ['point_of_sale', 'payment_mollie'],
    'data': [
        'security/ir.access.csv',
        'views/pos_payment_method_views.xml',
        'wizard/pos_mollie_terminal_wizard_views.xml',
    ],
    'assets': {
        'point_of_sale.payment_terminals': [
            'pos_mollie/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_mollie/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
