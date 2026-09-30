{
    'name': 'POS Cashdro Cash Machines',
    'category': 'Sales/Point of Sale',
    'summary': 'Integrate your POS with a Cashdro automatic cash payment device',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_cashdro/static/src/**/*',
            ('remove', 'pos_cashdro/static/src/app/**/*'),
        ],
        'point_of_sale._assets_pos': [
            'pos_cashdro/static/src/**/*',
            ('remove', 'pos_cashdro/static/src/backend/**/*'),
        ],
        'web.assets_unit_tests': [
            'pos_cashdro/static/tests/**/*',
            'pos_cashdro/static/src/cashdro_service.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
