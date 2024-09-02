# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheets and Attendance Analysis',
    'summary': 'Compare attendance hours with hours recorded in timesheets.',
    'description': """
    Compare attendance hours with hours recorded in timesheets.
    """,
    'category': 'Services/Timesheets',
    'version': '1.1',

    'depends': ['hr_timesheet', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_timesheet_attendance_report_security.xml',
        'report/hr_timesheet_attendance_report_view.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
