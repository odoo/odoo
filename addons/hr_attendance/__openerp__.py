# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Attendances',
    'version': '1.1',
    'category': 'Human Resources',
    'description': """
This module aims to manage employee's attendances.
==================================================

Keeps account of the attendances of the employees on the basis of the
actions(Sign in/Sign out) performed by them.
       """,
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['hr', 'report'],
    'data': [
        'security/hr_attendance_security.xml',
        'security/ir.model.access.csv',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_report.xml',
        'views/report_attendanceerrors.xml',
        'views/hr_attendance_templates.xml',
        'views/hr_department_views.xml',
        'wizard/hr_attendance_error_views.xml',
    ],
    'demo': ['data/hr_attendance_demo.xml'],
    'installable': True,
    'auto_install': False,
    #web
    'qweb': ["static/src/xml/attendance_templates.xml"],
}
