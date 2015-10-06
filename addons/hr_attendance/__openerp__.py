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
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'views/hr_attendance_view.xml',
        'views/hr_attendance_report.xml',
        'views/report_attendanceerrors.xml',
        'views/hr_attendance.xml',
        'views/hr_dashboard.xml',
        'wizard/hr_attendance_error_view.xml',
    ],
    'demo': ['demo/hr_attendance_demo.xml'],
    'installable': True,
    #web
    'qweb': ["static/src/xml/attendance.xml"],
}
