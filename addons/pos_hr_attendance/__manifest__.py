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
            'hr_attendance/static/src/public_kiosk/**/*',
            'hr_attendance/static/src/components/attendance_video_stream/**/*',
            'hr_attendance/static/src/components/break_duration_dialog/**/*',
            'hr_attendance/static/src/components/card_layout/**/*',
            'hr_attendance/static/src/components/confirmation/**/*',
            'hr_attendance/static/src/components/greetings/**/*',
            'hr_attendance/static/src/components/hooks/use_camera.js',
            'hr_attendance/static/src/components/kiosk_barcode/**/*',
            'hr_attendance/static/src/components/manual_selection/**/*',
            'hr_attendance/static/src/components/new_employee_dialog/**/*',
            'hr_attendance/static/src/components/pin_code/**/*',
            'hr_attendance/static/src/scss/kiosk/hr_attendance.css',
            'barcodes/static/src/components/barcode_scanner.*',
            'pos_hr_attendance/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_hr_attendance/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
