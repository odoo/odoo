# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Appointment Lead Generation',
    'version': '1.0',
    'category': 'Services/Appointment',
    'sequence': 2150,
    'summary': 'Generate leads when prospects schedule appointments',
    'website': 'https://www.odoo.com/app/appointments',
    'description': """
Allow to generate lead from Scheduled Appointments through your Website
-----------------------------------------------------------------------

""",
    'depends': ['appointment', 'crm'],
    'data': [
        'views/appointment_type_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'appointment_crm/static/src/views/**/*',
        ],
        'web.assets_tests': [
            'appointment_crm/static/tests/tours/**/*',
        ],
    },
}
