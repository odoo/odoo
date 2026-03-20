{
    'name': 'Events Product',
    'category': 'Marketing/Events',
    'depends': ['event', 'product', 'account'],
    'data': [
        'views/event_ticket_views.xml',
        'views/event_registration_views.xml',
        'data/event_product_data.xml',
    ],
    'demo': [
        'data/event_product_demo.xml',
        'data/event_demo.xml',
    ],
    'auto_install': True,
    'assets': {},
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
