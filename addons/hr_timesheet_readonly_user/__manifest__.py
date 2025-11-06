{
    'name': 'HR Timesheet - Read-only for Users',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Timesheets',
    'summary': 'Restrict timesheet editing to administrators only',
    'description': """
        This module restricts timesheet editing permissions:
        - Standard users can only view their own timesheets (read-only)
        - Only administrators can create, edit, or delete timesheets
    """,
    'author': 'Your Company',
    'depends': ['hr_timesheet'],
    'data': [
        'security/hr_timesheet_security.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
