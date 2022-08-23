# -*- coding: utf-8 -*-

{
    'name': 'Events Sales',
    'version': '1.2',
    'category': 'Marketing/Events',
    'website': 'https://www.odoo.com/app/events',
    'description': """
Creating registration with sales orders.
========================================

This module allows you to automate and connect your registration creation with
your main sale flow and therefore, to enable the invoicing feature of registrations.

It defines a new kind of service products that offers you the possibility to
choose an event category associated with it. When you encode a sales order for
that product, you will be able to choose an existing event of that category and
when you confirm your sales order it will automatically create a registration for
this event.
""",
    'depends': ['event', 'sale_management'],
    'data': [
        'views/event_ticket_views.xml',
        'views/event_registration_views.xml',
        'views/event_views.xml',
        'views/sale_order_views.xml',
        'data/event_sale_data.xml',
        'data/mail_templates.xml',
        'report/event_event_templates.xml',
        'report/event_sale_report_views.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'security/event_security.xml',
        'wizard/event_edit_registration.xml',
        'wizard/event_configurator_views.xml',
    ],
    'demo': [
        'data/event_sale_demo.xml',
        'data/event_demo.xml',  # needs event_sale_demo
        'data/event_registration_demo.xml',  # needs event_sale_demo
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'event_sale/static/src/**/*',
        ],
        'web.assets_tests': [
            'event_sale/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'event_sale/static/tests/event_configurator.test.js',
        ],
    },
    'license': 'LGPL-3',
}
