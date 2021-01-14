# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Events Booths",
    'category': 'Marketing/Events',
    'version': '1.0',
    'summary': "Manage event booths",
    'description': """
Manage event booths :
- Create booths for your favorite events
- Create multiple slots for your booths
- Register the slots to your partners
    """,
    'depends': ['event'],
    'data': [
        'security/ir.model.access.csv',

        'views/event_booth_registration_views.xml',
        'views/event_booth_slot_views.xml',
        'views/event_booth_views.xml',
        'views/event_views.xml',
    ],
    'demo': [
        'data/event_booth_demo.xml',
    ],
}
