{
    'name': 'POS Kitchen Lock',
    'version': '19.0.1.0.0',
    'author': 'Kosalan Balarajah',
    'category': 'Point of Sale',
    'summary': 'Lock sent kitchen lines for minimal-rights cashiers',
    'description': """
        Once an order line has been sent to the kitchen, minimal-rights
        employees (waitstaff) cannot reduce quantity, delete, or modify
        notes on that line. A manager PIN / manager login is required.
        Sent lines are visually greyed out to make the lock obvious.
    """,
    'depends': ['point_of_sale', 'pos_restaurant'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_kitchen_lock/static/src/css/kitchen_lock.css',
            'pos_kitchen_lock/static/src/js/kitchen_lock.js',
            'pos_kitchen_lock/static/src/xml/kitchen_lock.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
