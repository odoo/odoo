# -*- coding: utf-8 -*-
{
    'name': "Timesheets/attendances reporting",
    'description': """
    Module linking the attendance module to the timesheet app.
    """,
    'category': 'Hidden',
    'version': '1.0',

    'depends': ['hr_timesheet_sheet', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'report/hr_timesheet_attendance_report_view.xml',
        'views/hr_timesheet_sheet_views.xml',
        'views/hr_timesheet_attendance_config_settings_views.xml',
    ],
    'auto_install': True,
}
