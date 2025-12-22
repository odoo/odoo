# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "HR Attendance Holidays",
    'summary': """Attendance Holidays""",
    'category': 'Human Resources',
    'description': """
Convert employee's extra hours to leave allocations.
    """,
    'version': '1.0',
    'depends': ['hr_attendance', 'hr_holidays'],
    'auto_install': True,
    'data': [
        'views/hr_leave_allocation_views.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_employee_views.xml',
        'views/res_users_views.xml',
        'views/hr_leave_accrual_level_views.xml',
        'data/hr_holidays_attendance_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_holidays_attendance/static/src/xml/time_off_calendar.xml',
        ],
    },
    'license': 'LGPL-3',
}
