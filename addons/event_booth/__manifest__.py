# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Events Booths",
    'category': 'Marketing/Events',
    'version': '1.1',
    'summary': "Manage event booths",
    'description': """
Create booths for your favorite event.
    """,
    'depends': ['event'],
    'data': [
        'security/ir.model.access.csv',
        'views/event_booth_category_views.xml',
        'views/event_type_booth_views.xml',
        'views/event_booth_views.xml',
        'views/event_type_views.xml',
        'views/event_event_views.xml',
        'views/event_menus.xml',
        'data/event_booth_category_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_templates.xml',
    ],
    'demo': [
        'data/event_booth_demo.xml',
        'data/event_type_demo.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
