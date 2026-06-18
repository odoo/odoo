{
    'name': 'KSW - attendance leave',
    'category': 'Human Resources',
    'version': '19.0.1.0.0',
    'sequence': 1,
    'author': 'Mohammed Albadr',
    'summary': 'HR Attendance Leave for Odoo 19 Community Edition',
    'description': """
HR Attendance Leave
=====================
Connecting attendance records with leave management to be a list to choose from
    """,
    'license': 'LGPL-3',
    'depends': [
        'hr_biometric_attendance',
        'hr_holidays',
        'mail',
    ],
    'data': [
        # Security
        # 'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/attendance_issue_defaults.xml',

        # Views
        'views/hr_employee_views.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'KSW_attendance_leave/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
