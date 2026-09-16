{
    'name': 'PoS Square',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'summary': 'Integrate your PoS with the Square Point of Sale app',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_square/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_square/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
