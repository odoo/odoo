# -*- coding: utf-8 -*-

{
    'name': 'Events Sales',
    'version': '1.1',
    'category': 'Tools',
    'website': 'https://www.odoo.com/page/events',
    'description': """
Creating registration with sale orders.
=======================================

This module allows you to automate and connect your registration creation with
your main sale flow and therefore, to enable the invoicing feature of registrations.

It defines a new kind of service products that offers you the possibility to
choose an event category associated with it. When you encode a sale order for
that product, you will be able to choose an existing event of that category and
when you confirm your sale order it will automatically create a registration for
this event.
""",
    'depends': ['event', 'sale'],
    'data': [
        'views/event.xml',
        'views/product.xml',
        'views/sale_order.xml',
        'event_sale_data.xml',
        'report/event_event_templates.xml',
        'security/ir.model.access.csv',
        'wizard/event_edit_registration.xml',
    ],
    'demo': ['event_demo.xml'],
    'test': ['test/confirm.yml'],
    'installable': True,
    'auto_install': True
}
