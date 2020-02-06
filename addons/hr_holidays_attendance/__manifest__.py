# -*- coding: utf-8 -*-
{
    'name': "HR Attendance Holidays",
    'summary': """""",
    'category': 'Human Resources',
    'description': """
Hides the attendance presence button when an employee is on leave.
    """,
    'version': '1.0',
    'depends': ['hr_attendance', 'hr_holidays'],
    'auto_install': True,
    'data': [
        'data/hr_holidays_data.xml',
        'security/ir.model.access.csv',
        'security/hr_holidays_attendance_security.xml',
        'wizard/deduct_extra_hours_wizard_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_type_views.xml',
    ],
}
