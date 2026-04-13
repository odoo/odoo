{
    'name': 'KSW Unpaid Leave',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Unpaid leave with multi-step approval and attendance sheet integration',
    'description': """
KSW Unpaid Leave
================
Adds an Unpaid Leave type with:
- 4-step multi-step approval (DM → HR → GM Initial → GM Final)
- Calendar-day duration counting (Saudi labor law)
- Attendance sheet integration: approved days locked as absent
- Annual leave accrual impact: unpaid days reduce effective service days
- Printable Leave Approval Report (shared for annual & unpaid)
    """,
    'author': 'Mohammed Albadr',
    'license': 'LGPL-3',
    'depends': [
        'KSW_annual_leave',
        'KSW_attendance_sheet',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/leave_type_data.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/attendance_sheet_views.xml',
        'wizard/absent_days_wizard_views.xml',
        'reports/leave_approval_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


