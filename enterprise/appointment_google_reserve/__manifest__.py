{
    'name': 'Appointment Google Reserve',
    'version': '1.0',
    'category': 'Productivity',
    'description': """Enable a link between your appointment type and the google API""",
    'depends': [
        'appointment'
    ],
    'installable': True,
    'license': 'OEEL-1',
    'data': [
        'data/ir_cron_data.xml',
        'views/appointment_type_views.xml',
        'views/google_reserve_merchant_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/google_reserve_demo.xml',
    ],
}
