# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "HR Attendance Holidays",
    'summary': """Attendance Holidays""",
    'category': 'Human Resources',
    'description': """
Convert employee's extra hours to leave allocations.
    """,
    'depends': ['hr_attendance', 'hr_time'],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/hr_time_allocation_views.xml',
        'views/hr_work_entry_type_views.xml',
        'views/hr_time_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_time_accrual_level_views.xml',
        'views/hr_time_attendance_report_views.xml',
        'views/hr_attendance_overtime_views.xml',
        'data/hr_time_attendance_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_time_attendance/static/src/**/*',
        ],
        'web.assets_tests': [
            'hr_time_attendance/static/tests/tours/*.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
