{
    'name': 'Presenly → Payroll Bridge',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Bridges approved Presenly overtime requests into Custom Payroll slips',
    'description': """
Presenly → Payroll Bridge
=========================
Overtime on payslips (custom.payroll.slip) now comes ONLY from approved
Presenly Overtime Requests (presenly.overtime.request, state = 'approved')
within the payroll period. The legacy calculation from hr.attendance
worked hours is removed. A manual override on the slip still wins.
    """,
    'author': 'Presenly',
    'website': '',
    'depends': [
        'hr_payroll_custom',
        'presenly',
    ],
    'data': [
        'views/custom_payroll_slip_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}