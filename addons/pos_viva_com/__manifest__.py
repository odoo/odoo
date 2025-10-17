{
    'name': 'PoS Viva.com',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'summary': 'Integrate your PoS with a Viva.com payment terminal',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_viva_com/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_viva_com/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_viva_com/static/tests/unit/data/**/*'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
