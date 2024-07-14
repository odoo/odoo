# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Recruitment tracking on appointments",
    'version': "1.0",
    'category': 'Services/Appointment',
    'summary': "Keep track of recruitment appointments",
    'description': """
Keeps track of all appointments related to applicants.
""",
    'depends': ['appointment', 'hr_recruitment'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_tests': [
            'appointment_hr_recruitment/static/tests/tours/**/*',
        ],
    },
    'demo': [
        'data/appointment_hr_recruitment_demo.xml',
        'data/mail_template_demo.xml',
    ],
}
