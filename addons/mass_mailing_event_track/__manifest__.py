# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass mailing on track speakers',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Mass mail event track speakers
==============================

Bridge module adding UX requirements to ease mass mailing of event track speakers.
        """,
    'depends': ['website_event_track', 'mass_mailing'],
    'data': [
        'views/event_views.xml'
    ],
    'auto_install': True,
}
