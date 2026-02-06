
{
    'name': 'Maintenance',
    'sequence': 100,
    'category': 'Supply Chain/Maintenance',
    'description': """
Track equipment and maintenance requests""",
    'depends': ['mail'],
    'summary': 'Track equipment and manage maintenance requests',
    'website': 'https://www.odoo.com/app/maintenance',
    'data': [
        'security/maintenance.xml',
        'data/maintenance_data.xml',
        'data/mail_activity_type_data.xml',
        'data/mail_message_subtype_data.xml',
        'views/maintenance_views.xml',
        'views/mail_activity_views.xml',
        'views/res_config_settings_views.xml',
        'security/ir.access.csv',
    ],
    'demo': ['data/maintenance_demo.xml'],
    'application': True,
    'assets': {
        'web.assets_backend': [
            'maintenance/static/src/**/*',
        ],
        'web.assets_tests': [
            'maintenance/static/tests/tours/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
