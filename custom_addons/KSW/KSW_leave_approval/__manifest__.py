{
    'name': 'KSW Leave Approval',
    'version': '19.0.1.0.0',
    'author': 'Mohammed Albadr',
    'category': 'Human Resources',
    'summary': 'Custom 2-step approval for time off (Direct Manager -> HR Manager)',
    'description': """
        Implements a robust 2-step approval process for all non-annual leaves:
        1. First approval: Must be done by the employee's Direct Manager.
        2. Second approval: Must be done by the configured HR Manager.
        
        The HR Manager can be configured in settings.
    """,
    'depends': [
        'hr_holidays',
        'KSW_annual_leave',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'license': 'LGPL-3',
}
