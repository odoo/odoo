{
    'name': 'POS Kitchen Lock',
    'version': '19.0.2.0.0',
    'author': 'Kosalan Balarajah',
    'category': 'Point of Sale',
    'summary': 'Lock sent kitchen lines for minimal-rights cashiers',
    'description': """
        Once an order line has been sent to the kitchen, minimal-rights
        employees (waitstaff) cannot reduce quantity, delete, or modify
        notes on that line.

        When a minimal cashier tries to modify a sent line, a manager
        selection popup appears. The manager selects their name, enters
        their PIN, and the session switches to the manager. A sticky
        "Lock Session" notification lets the manager hand the terminal
        back to the waitstaff when finished.
    """,
    'depends': ['point_of_sale', 'pos_restaurant'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_kitchen_lock/static/src/css/kitchen_lock.css',
            'pos_kitchen_lock/static/src/js/manager_override_dialog.js',
            'pos_kitchen_lock/static/src/js/kitchen_lock.js',
            'pos_kitchen_lock/static/src/xml/manager_override_dialog.xml',
            'pos_kitchen_lock/static/src/xml/kitchen_lock.xml',
        ],
        'hr_attendance.assets_public_attendance': [
            'pos_kitchen_lock/static/src/css/kiosk_overrides.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
