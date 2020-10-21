# -*- coding: utf-8 -*-

{
    'name': 'Online Event Booths',
    'category': 'Marketing/Events',
    'version': '1.0',
    'summary': 'Events, display your booths on your website',
    'description': """
Display your booths on your website for the users to register.
    """,
    'depends': ['website_event', 'event_booth'],
    'data': [
        'views/assets.xml',
        'views/event_views.xml',

        'views/event_booth_templates.xml',
    ],
    'demo': [
        'data/event_booth_demo.xml',
    ],
    'auto_install': True,
}
