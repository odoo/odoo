# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Full Event Flow',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """
This module will test the main event flows of Odoo, both frontend and backend.
It installs sale capabilities, front-end flow, eCommerce, questions and
automatic lead generation..
""",
    'depends': [
        'event',
        'event_crm',
        'event_sale',
        'website_event_crm_questions',
        'website_event_questions',
        'website_event_sale',
        'website_event_track',
    ],
    'demo': [],
    'data': [],
    'installable': True,
}
