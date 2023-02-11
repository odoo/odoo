# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event Attendees SMS Marketing',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
SMS Marketing on event attendees
================================

Bridge module adding UX requirements to ease SMS marketing o, event attendees.
        """,
    'depends': [
        'event',
        'mass_mailing',
        'mass_mailing_sms',
        'sms',
    ],
    'data': [
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
