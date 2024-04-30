{
    'name': 'Events Product',
    'version': '1.0',
    'category': 'Marketing/Events',
    'depends': ['event', 'product', 'account'],
    'data': [
        'views/event_ticket_views.xml',
        'data/event_product_data.xml',
    ],
    'demo': [
        'data/event_product_demo.xml',
        'data/event_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {},
    'license': 'LGPL-3',
}
