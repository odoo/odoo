# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Appointment Testing Module',
    'version': "1.0",
    'category': 'Hidden/Tests',
    'sequence': 9999,
    'summary': 'Appointment Testing Module',
    'website': 'https://www.odoo.com/app/appointments',
    'description': """
Take into account the working schedule (sick leaves, part time, ...) of employees when scheduling appointments
--------------------------------------------------------------------------------------------------------------
""",
    'depends': [
        'appointment_crm',
        'appointment_hr',
        'website_appointment',
    ],
    'license': 'OEEL-1',
}
