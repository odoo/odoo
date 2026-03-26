{
    'name': 'KSW - Odoo 19 HR Payroll',
    'category': 'Human Resources/Payroll',
    'version': '19.0.1.0.0',
    'sequence': 1,
    'author': 'Mohammed Albadr',
    'summary': 'HR Payroll Management for Odoo 19 Community Edition',
    'description': """
HR Payroll Management
=====================
Manage employee payroll, salary rules, payslips and more.
    """,
    'license': 'LGPL-3',
    'depends': [
        'om_hr_payroll',
        'KSW_attendance_leave',
        'KSW_working_schedule',
        'mail',
    ],
    'data': [
        # Security
        # 'security/hr_payroll_security.xml',
        # 'security/ir.model.access.csv',

        # Views
        'views/hr_employee_view.xml',
        'views/hr_attendance_views.xml',

        # Reports
        'report/report_payslip_deduction_templates.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': True,
}
