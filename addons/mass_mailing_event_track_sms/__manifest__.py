# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Track Speakers SMS Marketing',
    'category': 'Marketing/Email Marketing',
    'description':
        """
SMS Marketing on event track speakers
=====================================

Bridge module adding UX requirements to ease SMS marketing on event track
speakers..
        """,
    'depends': [
        'mass_mailing_event_track',
        'website_mass_mailing_sms',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
