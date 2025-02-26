# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event Attendees SMS Marketing',
    'category': 'Marketing/Email Marketing',
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
        'mass_mailing_event',
        'mass_mailing_sms',
        'sms',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
