{
    'name': 'KSW - Odoo 19 working schedule',
    'version': '19.0.1.0.0',
    'sequence': 1,
    'author': 'Mohammed Albadr',
    'summary': 'Adding work schedule fields to employee model',
    'description': """
Work Schedule Management
=====================
This module extends the employee model to include fields for managing work schedules. It allows you to assign both a main and temporary work schedule to each employee, which can be used for attendance analysis and scheduling purposes.
    """,
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
    ],
    'data': [
        # Security
        # 'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',

        # Views
        'views/hr_employee_views.xml',
        'views/resource_calendar_group_views.xml',
        'views/resource_calendar_views.xml',

    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': True,
}
