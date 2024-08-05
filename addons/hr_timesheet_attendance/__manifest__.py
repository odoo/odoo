# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheets and Attendance Analysis',
    'summary': 'Compare attendance hours with hours recorded in timesheets.',
    'description': """
    Compare attendance hours with hours recorded in timesheets.
    """,
    'category': 'Human Resources/Attendances',
    'version': '1.1',

    'depends': ['hr_timesheet', 'hr_attendance'],
    'data': [
        'report/hr_timesheet_attendance_report_view.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
