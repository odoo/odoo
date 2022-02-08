# -*- coding: utf-8 -*-

{
    'name': 'Booths Sale/Exhibitors Bridge',
    'category': 'Marketing/Events',
    'version': '1.0',
    'summary': 'Bridge module between website_event_booth_exhibitor and website_event_booth_sale.',
    'description': """
    """,
    'depends': ['website_event_exhibitor', 'website_event_booth_sale'],
    'data': [],
    'auto_install': True,
    'assets': {
        'web.assets_tests': [
            'website_event_booth_sale_exhibitor/static/tests/tours/website_event_booth_sale_exhibitor.js',
        ],
    },
    'license': 'LGPL-3',
}
