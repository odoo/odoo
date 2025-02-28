{
    'name': 'POS - Salesperson',
    'description': """
    Able to select salesperson(employee) on POS (billing screen).
    """,
    'version': '1.0',
    'depends': ['point_of_sale','pos_hr'],
    'data': [
        'views/pos_order_view.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_salesperson/static/src/**/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
