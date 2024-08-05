# -*- coding: utf-8 -*-
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
    'depends': ['hr', 'barcodes'],
    'data': [
        'security/hr_attendance_security.xml',
        'security/ir.model.access.csv',
        'views/hr_attendance_view.xml',
        'views/hr_attendance_overtime_view.xml',
        'views/hr_department_view.xml',
        'views/hr_employee_view.xml',
        'views/res_config_settings_views.xml',
        'views/hr_attendance_kiosk_templates.xml'
    ],
    'demo': [
        'data/hr_attendance_demo.xml'
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'hr_attendance/static/src/**/*.js',
            'hr_attendance/static/src/**/*.xml',
            'hr_attendance/static/src/scss/views/*.scss'
        ],
        'web.qunit_suite_tests': [
            'hr_attendance/static/tests/hr_attendance_mock_server.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'hr_attendance/static/tests/hr_attendance_mock_server.js',
        ],
        'hr_attendance.assets_public_attendance': [
            # Define attendance variables (takes priority)
            'hr_attendance/static/src/scss/kiosk/primary_variables.scss',

            # Front-end libraries
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_primary_variables'),
            'hr_attendance/static/src/scss/kiosk/bootstrap_overridden.scss',
            ('include', 'web._assets_frontend_helpers'),
            'web/static/lib/jquery/jquery.js',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            ('include', 'web._assets_bootstrap_frontend'),
            ('include', 'web._assets_bootstrap_backend'),
            '/web/static/lib/odoo_ui_icons/*',
            '/web/static/lib/bootstrap/scss/_functions.scss',
            '/web/static/lib/bootstrap/scss/_mixins.scss',
            '/web/static/lib/bootstrap/scss/utilities/_api.scss',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            ('include', 'web._assets_core'),

            # Public Kiosk app and its components
            "hr_attendance/static/src/public_kiosk/**/*",
            'hr_attendance/static/src/components/**/*',

            'hr_attendance/static/src/scss/kiosk/hr_attendance.scss',
            "web/static/src/views/fields/formatters.js",

            # document link
            "web/static/src/session.js",
            "web/static/src/views/widgets/standard_widget_props.js",
            "web/static/src/views/widgets/documentation_link/*",

            # Barcode reader utils
            "web/static/src/webclient/barcode/barcode_scanner.js",
            "web/static/src/webclient/barcode/barcode_scanner.xml",
            "web/static/src/webclient/barcode/barcode_scanner.scss",
            "web/static/src/webclient/barcode/crop_overlay.js",
            "web/static/src/webclient/webclient_layout.scss",
            "web/static/src/webclient/barcode/crop_overlay.xml",
            "web/static/src/webclient/barcode/crop_overlay.scss",
            "web/static/src/webclient/barcode/ZXingBarcodeDetector.js",
            "barcodes/static/src/components/barcode_scanner.js",
            "barcodes/static/src/components/barcode_scanner.xml",
            "barcodes/static/src/components/barcode_scanner.scss",
            "barcodes/static/src/barcode_service.js",

        ]
    },
    'license': 'LGPL-3',
}
