# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Track Speakers SMS Marketing',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
SMS Marketing on event track speakers
=====================================

Bridge module adding UX requirements to ease SMS marketing on event track
speakers..
        """,
    'depends': [
        'mass_mailing',
        'mass_mailing_sms',
        'sms',
        'website_event_track'
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
