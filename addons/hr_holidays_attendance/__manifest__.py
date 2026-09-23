{
    "name": "HR Attendance Holidays",
    "version": "1.0",
    "category": "Human Resources",
    "summary": "Attendance Holidays",
    "description": """
Convert employee's extra hours to leave allocations.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr_attendance",
        "hr_holidays",
    ],
    "data": [
        "security/ir.access.csv",
        "views/hr_leave_allocation_views.xml",
        "views/hr_leave_type_views.xml",
        "views/hr_leave_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_leave_accrual_level_views.xml",
        "views/hr_leave_attendance_report_views.xml",
        "views/hr_attendance_overtime_views.xml",
        "data/hr_holidays_attendance_data.xml",
        "views/hr_holidays_attendance_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_holidays_attendance/static/src/**/*",
        ],
    },
    "auto_install": True,
}
