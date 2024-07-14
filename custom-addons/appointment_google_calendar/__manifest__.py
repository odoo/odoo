# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Appointment Google Calendar',
    'version': '1.0',
    'category': 'Productivity',
    'description': """Enable choosing a Google Calendar videoconference link to give to your clients for an appointment.""",
    'depends': ['google_calendar', 'appointment'],
    'installable': True,
    'license': 'OEEL-1',
    'data': [
        'views/appointment_templates_validation.xml',
        'views/appointment_type_views.xml',
    ],
}
