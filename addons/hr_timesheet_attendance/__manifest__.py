{
    "name": "Timesheets/attendances reporting",
    "version": "1.1",
    "category": "Human Resources/Attendances",
    "description": """
    Module linking the attendance module to the timesheet app.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr_timesheet",
        "hr_attendance",
    ],
    "data": [
        "security/ir.access.csv",
        "reports/hr_timesheet_attendance_report_view.xml",
        "views/hr_timesheet_attendance_menus.xml",
    ],
    "auto_install": True,
}
