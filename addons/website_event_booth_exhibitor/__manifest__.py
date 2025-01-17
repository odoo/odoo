# -*- coding: utf-8 -*-

{
    'name': 'Booths/Exhibitors Bridge',
    'category': 'Marketing/Events',
    'version': '1.1',
    'summary': 'Event Booths, automatically create a sponsor.',
    'description': """
Automatically create a sponsor when renting a booth.
    """,
    'depends': ['website_event_exhibitor', 'website_event_booth'],
    'data': [
        'data/event_booth_category_data.xml',

        'views/event_booth_category_views.xml',
        'views/event_booth_views.xml',

        'views/event_booth_registration_templates.xml',
        'views/event_booth_templates.xml',
        'views/mail_templates.xml'
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            '/website_event_booth_exhibitor/static/src/interactions/booth_sponsor_details.js',
        ],
        'web.assets_tests': [
            'website_event_booth_exhibitor/static/tests/tours/website_event_booth_exhibitor_steps.js',
            'website_event_booth_exhibitor/static/tests/tours/website_event_booth_exhibitor.js',
        ],
    },
    'license': 'LGPL-3',
}
