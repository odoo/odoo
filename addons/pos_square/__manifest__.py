{
    'name': 'PoS Square',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'data': [
        'views/pos_payment_method_views.xml',
        'views/templates.xml',
    ],
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_square/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
