# -*- coding: utf-8 -*-

{
    'name': 'Events Product',
    'version': '1.3',
    'category': 'Marketing/Events',
    'depends': ['event', 'product'],
    'data': [
        'views/event_ticket_views.xml',
        'security/ir.model.access.csv',
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
