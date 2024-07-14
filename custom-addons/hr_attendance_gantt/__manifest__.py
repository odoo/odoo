# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Attendance Gantt",
    'summary': """Gantt view for Attendance""",
    'description': """
    Gantt view for Attendance
    """,
    'category': 'Human Resources/Attendances',
    'version': '1.0',
    'depends': ['hr_attendance', 'hr_gantt'],
    'auto_install': True,
    'data': [
        'views/hr_attendance_gantt.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'hr_attendance_gantt/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr_attendance_gantt/static/tests/**/*',
        ],
    },
    'license': 'OEEL-1',
}
