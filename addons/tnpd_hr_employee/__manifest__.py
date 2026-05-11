# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

{
    'name': 'TNPD Prison HR Employee Extension',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Extends hr.employee with TNPD prison department fields',
    'description': """
TNPD Prison HR Employee Extension
==================================
Adds prison-department-specific fields to the standard Odoo Employee form,
including service details, demographic data, station postings, disciplinary
records, service history, achievements, and family information.

All fields are non-destructive additions via model inheritance (_inherit).
No core Odoo files are modified.
    """,
    'author': 'TNPD',
    'website': '',
    'license': 'LGPL-3',

    'depends': ['hr'],

    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
