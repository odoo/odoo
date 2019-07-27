# -*- coding: utf-8 -*-
{
    'name': "HR Attendance Holidays",
    'summary': """""",
    'category': 'HR',
    'description': """
        Hides attendance presence stat button when an employee is on leave.
    """,
    'version': '1.0',
    'depends': ['hr_attendance', 'hr_holidays'],
    'auto_install': True,
    'data': [
        'views/hr_employee_views.xml',
    ],
}
