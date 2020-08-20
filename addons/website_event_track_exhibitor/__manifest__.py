# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Event Exhibitors',
    'category': 'Marketing/Events',
    'sequence': 1004,
    'version': '1.0',
    'summary': 'Event: upgrade sponsors to exhibitors',
    'website': 'https://www.odoo.com/page/events',
    'description': "",
    'depends': [
        'website_event_track',
        'website_jitsi',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/assets.xml',
        'views/event_sponsor_views.xml',
        'views/event_event_views.xml',
        'views/event_exhibitor_templates_list.xml',
        'views/event_exhibitor_templates_page.xml',
        'views/event_type_views.xml',
    ],
    'demo': [
        'data/event_demo.xml',
        'data/event_sponsor_demo.xml',
    ],
    'application': False,
    'installable': True,
}
