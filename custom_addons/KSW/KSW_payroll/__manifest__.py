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
        'mail',
    ],
    'data': [
        # Security
        # 'security/hr_payroll_security.xml',
        # 'security/ir.model.access.csv',

        # Views
        'views/hr_employee_view.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': True,
}
