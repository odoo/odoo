# -*- coding: utf-8 -*-

{
    'name': 'Point of Sale Events',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'description': """
Creating registration through the Point of Sale.
================================================

This module allows you to automate and connect your registration creation with
your main point of sale flow.

It defines a new kind of service products that offers you the possibility to
choose an event category associated with it. When you encode a pos order for
that product, you will be able to choose an existing event of that category and
when you validate your pos order it will automatically create a registration for
this event.
""",
    'depends': ['event', 'event_product', 'point_of_sale'],
    'data': [
        'data/pos_event_data.xml',
        'data/pos_event_demo.xml',
    ],
    'installable': True,
    'auto_install': ['event', 'point_of_sale'],
    'assets': {
        'point_of_sale.assets': [
            'pos_event/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
