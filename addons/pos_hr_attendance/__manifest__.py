{
    'name': "POS - Attendances",
    'category': "Sales/Point of Sale",
    'summary': 'Link module between Point of Sale (HR) and Attendances',
    'description': """
Manage employees attendance from Point Of Sale.
    """,
    'depends': ['pos_hr', 'hr_attendance'],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            ('include', 'hr_attendance._base_public_kiosk_assets'),
            'pos_hr_attendance/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_hr_attendance/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
