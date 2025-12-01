{
    'name': "addons/mass_mailing_hr",
    'summary': "Bridge between Mass Mailing and HR",
    'description': """
This module adds additional functionality for mailing creation when both MassMailing and HR are installed at the same time.
    """,
    'author': "Odoo S.A.",
    'category': 'Marketing/Email Marketing',
    'depends': ['mass_mailing', 'hr'],
    'auto_install': True,
    'data': [
        'views/hr_employee_views.xml',
    ],
    'license': 'LGPL-3',
}
