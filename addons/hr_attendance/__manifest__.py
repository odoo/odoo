# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Attendances',
    'version': '2.0',
    'category': 'Human Resources/Attendances',
    'sequence': 240,
    'summary': 'Track employee attendance',
    'description': """
This module aims to manage employee's attendances.
==================================================

Keeps account of the attendances of the employees on the basis of the
actions(Check in/Check out) performed by them.
       """,
    'website': 'https://www.odoo.com/app/employees',
    'depends': ['hr', 'hr_work_entry', 'barcodes', 'base_geolocalize'],
    'data': [
        'data/hr_attendance_data.xml',
        'security/hr_attendance_security.xml',
        'views/hr_attendance_view.xml',
        'views/hr_department_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_employee_public_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_attendance_kiosk_templates.xml',
        'views/hr_version_views.xml',
        'views/hr_contract_template_views.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'data/hr_attendance_demo.xml'
    ],
    'other_files': [
        'data/scenarios/hr_attendance_scenario.xml',
    ],
    'application': True,
    'assets': {
        'web.assets_backend': [
            'hr_attendance/static/src/**/*.js',
            'hr_attendance/static/src/**/*.xml',
            'hr_attendance/static/src/scss/views/*.css',
            'hr_attendance/static/src/components/attendance_dashboard/*.css',
        ],
        'web.assets_unit_tests': [
            'hr_attendance/static/tests/*.test.js',
        ],
        'web.assets_tests': [
            'hr_attendance/static/tests/tours/**/*',
        ],
        'hr_attendance._base_public_kiosk_assets': [
            "hr_attendance/static/src/public_kiosk/**/*",
            "hr_attendance/static/src/components/attendance_video_stream/**/*",
            "hr_attendance/static/src/components/break_duration_dialog/**/*",
            "hr_attendance/static/src/components/card_layout/**/*",
            "hr_attendance/static/src/components/confirmation/**/*",
            "hr_attendance/static/src/components/greetings/**/*",
            "hr_attendance/static/src/components/hooks/use_camera.js",
            "hr_attendance/static/src/components/kiosk_barcode/**/*",
            "hr_attendance/static/src/components/manual_selection/**/*",
            "hr_attendance/static/src/components/new_employee_dialog/**/*",
            "hr_attendance/static/src/components/pin_code/**/*",
            'hr_attendance/static/src/scss/kiosk/hr_attendance.css',
            "barcodes/static/src/components/barcode_scanner.js",
            "barcodes/static/src/components/barcode_scanner.xml",
            "barcodes/static/src/components/barcode_scanner.css",
            "barcodes/static/src/barcode_plugin.js",
        ],
        'hr_attendance.assets_public_attendance': [
            # Define attendance variables (takes priority)
            'hr_attendance/static/src/scss/kiosk/primary_variables.scss',

            # Front-end libraries
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_mixins.scss',
            'web/static/src/scss/functions.scss',
            'web/static/src/scss/mixins_forwardport.scss',
            'web/static/src/scss/bs_mixins_overrides.scss',
            'web/static/src/scss/utils.scss',
            'web/static/src/scss/primary_variables.scss',
            'web/static/src/**/*.variables.scss',
            'web/static/src/scss/secondary_variables.scss',
            'hr_attendance/static/src/scss/kiosk/bootstrap_overridden.scss',
            'web/static/src/scss/bootstrap_overridden_frontend.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            ('include', 'web._assets_bootstrap'),
            ('after', 'web/static/src/scss/utilities_custom.scss', 'web/static/src/scss/utilities_custom_backend.scss'),
            'web/static/src/scss/bootstrap_review_frontend.scss',
            'web/static/src/scss/bootstrap_review_backend.scss',
            'web/static/src/scss/css_variables.scss',
            ('include', 'web.icons_fonts'),
            ('include', 'web._assets_core'),

            'hr_attendance/static/src/scss/kiosk/kiosk_root.css',
            ('include', 'hr_attendance._base_public_kiosk_assets'),
            "web/static/src/views/fields/formatters.js",

            # document link
            "web/static/src/session.js",
            "web/static/src/views/widgets/standard_widget_props.js",
            "web/static/src/views/widgets/documentation_link/*",

            ('after', 'hr_attendance/static/src/scss/kiosk/primary_variables.scss', 'hr_attendance/static/src/scss/css_variables.scss'),

        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
