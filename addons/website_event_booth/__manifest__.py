# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        'security/ir.model.access.csv',
        'security/event_booth_security.xml',
        'views/event_type_views.xml',
        'views/event_event_views.xml',
        'views/event_booth_registration_templates.xml',
        'views/event_booth_templates.xml',
    ],
    'demo': [
        'data/event_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            '/website_event_booth/static/src/interactions/*',
            '/website_event_booth/static/src/scss/website_event_booth.scss',
            '/website_event_booth/static/src/xml/event_booth_registration_templates.xml',
        ],
    },
    'license': 'LGPL-3',
}
