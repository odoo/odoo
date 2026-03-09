{
    'name': 'POS Cashmatic Cash Machines',
    'category': 'Sales/Point of Sale',
    'summary': 'Integrate your POS with a cash matic automatic cash payment device',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cashmatic/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_cashmatic/static/tests/**/*',
            'pos_cashmatic/static/src/cashmatic_service.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
