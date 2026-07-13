# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event Attendees SMS Marketing',
    'category': 'Marketing/Email Marketing',
    'description':
        """
SMS Marketing on event attendees
================================

Bridge module adding UX requirements to ease SMS marketing o, event attendees.
        """,
    'depends': [
        'mass_mailing_event',
        'mass_mailing_sms',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
