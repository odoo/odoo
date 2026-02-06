# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "HR Attendance Holidays",
    'summary': """Attendance Holidays""",
    'category': 'Human Resources',
    'description': """
Convert employee's extra hours to leave allocations.
    """,
    'depends': ['hr_attendance', 'hr_holidays'],
    'auto_install': True,
    'data': [
        'views/hr_leave_allocation_views.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_accrual_level_views.xml',
        'views/hr_leave_attendance_report_views.xml',
        'views/hr_attendance_overtime_views.xml',
        'data/hr_holidays_attendance_data.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_holidays_attendance/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
