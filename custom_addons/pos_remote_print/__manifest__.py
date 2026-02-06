{
    'name': 'POS Remote Print',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'Laxya',
    'summary': 'Kitchen Printing for Remote Orders',
    'description': """
        Handles printing of POS orders created via API.
        - Uses Bus to notify active tablets.
        - Tablets claim order and print to kitchen.
    """,
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale.assets': [
            'pos_remote_print/static/src/js/remote_print.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
