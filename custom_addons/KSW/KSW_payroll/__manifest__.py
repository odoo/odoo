{
    'name': 'KSW - Odoo 19 HR Payroll',
    'category': 'Human Resources/Payroll',
    'version': '19.0.1.1.0',
    'sequence': 1,
    'author': 'Mohammed Albadr',
    'summary': 'HR Payroll Management for Odoo 19 Community Edition',
    'description': """
HR Payroll Management
=====================
Manage employee payroll, salary rules, payslips and more.

Extends om_hr_payroll with:
* Worked-day lines populated from actual hr.attendance records
  (biometric employees get full issue breakdown; attendance-sheet
   employees get attended vs absent only).
* Attendance Deduction salary rule (ATTDED) that reads the monetary
  deduction total from the ATT_DED worked-day line.
* Vacation-return guard: payslip computation is blocked when an
  employee has an approved annual leave whose return is not yet
  HR-confirmed.
    """,
    'license': 'LGPL-3',
    'depends': [
        'om_hr_payroll',
        'KSW_attendance_leave',
        'KSW_annual_leave',
        'KSW_attendance_sheet',
        'KSW_working_schedule',
        'mail',
    ],
    'data': [
        # Security
        # 'security/hr_payroll_security.xml',
        # 'security/ir.model.access.csv',

        # Data
        'data/salary_rule_deduction.xml',

        # Views
        'views/hr_employee_view.xml',
        'views/hr_attendance_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_version_views.xml',
        'views/res_config_settings_views.xml',

        # Reports
        'report/report_payslip_deduction_templates.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': True,
}
