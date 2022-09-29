# -*- coding: utf-8 -*-

{
    'name': 'Online Event Booth Sale',
    'category': 'Marketing/Events',
    'version': '1.0',
    'summary': 'Events, sell your booths online',
    'description': """
Use the e-commerce to sell your event booths.
    """,
    'depends': ['event_booth_sale', 'website_event_booth', 'website_sale'],
    'data': [
        'views/event_booth_templates.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            '/website_event_booth_sale/static/src/js/booth_register.js',
        ],
        'web.assets_tests': [
            '/website_event_booth_sale/static/tests/tours/**/**.js'
        ],
    },
    'license': 'LGPL-3',
}
