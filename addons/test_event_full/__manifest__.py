# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Full Event Flow',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """
This module will test the main event flows of Odoo, both frontend and backend.
It installs sale capabilities, front-end flow, eCommerce, questions and
automatic lead generation, full Online support, ...
""",
    'depends': [
        'event',
        'event_booth',
        'event_crm',
        'event_sale',
        'website_event_booth_sale_exhibitor',
        'website_event_crm_questions',
        'website_event_exhibitor',
        'website_event_questions',
        'website_event_meet',
        'website_event_sale',
        'website_event_track',
        'website_event_track_live',
        'website_event_track_quiz',
    ],
    'installable': True,
    'assets': {
        'web.assets_tests': [
            'test_event_full/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
