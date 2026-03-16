{
    'name': 'KSW Annual Leave',
    'version': '19.0.1.1.0',
    'category': 'Human Resources',
    'summary': 'Auto-computed annual leave allocation dashboard',
    'description': """
        Automatically calculates each employee's annual leave entitlement
        from their joining date to today using daily proration:
        - 21 days/year for the first 5 years
        - 30 days/year after 5 years
        Subtracts approved leaves taken and shows the remaining balance.
        Records are auto-created for all employees and refreshed daily
        by a scheduled action.
    """,
    'depends': [
        'hr_holidays',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_leave_type_views.xml',
        'views/annual_leave_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}


