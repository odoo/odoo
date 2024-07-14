# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Events Organization Add-on",
    'summary': "Add views and tweaks on event",
    'description': """This module helps for analyzing event registrations.
For that purposes it adds

  * a cohort analysis on attendees;
  * a gantt view on events;

    """,
    'category': 'Marketing/Events',
    'depends': ['event', 'web_cohort', 'web_gantt', 'web_map'],
    'data': [
        'views/event_event_views.xml',
        'views/event_registration_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
