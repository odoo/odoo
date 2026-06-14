{
    'name': 'KSW - Base Security Extensions',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Extended security groups and rules for Employees and Attendances',
    'author': 'KSW',
    'depends': ['hr', 'hr_attendance', 'hr_holidays'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
