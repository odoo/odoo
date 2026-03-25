{
    'name': 'KSW Attendance Sheet',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'sequence': 1,
    'author': 'Mohammed Albadr',
    'summary': 'Monthly attendance sheet for non-biometric employees',
    'description': """
KSW Attendance Sheet
====================
Manages monthly attendance for employees who do not use biometric
punch-in/punch-out.  Their manager reviews each month and marks
absent days; all other workdays default to "present".  On confirmation
the module creates hr.attendance records tagged as auto-generated so
the payroll pipeline can consume them identically to biometric records.
    """,
    'license': 'LGPL-3',
    'depends': [
        'hr_biometric_attendance',
        'KSW_working_schedule',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/attendance_sheet_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

