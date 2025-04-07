{
    'name': "POS Salesperson Assignment",
    'description': """
    Module to select salesperson on POS billing screen.
    """,
    'version': '1.0',
    'depends': ['point_of_sale', 'pos_hr'],
    'license': 'LGPL-3',
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_add_salesperson/static/src/**/*',
        ],
    },
    'data': [
        'views/pos_order_view.xml'
    ]
}
