# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'IoT for PoS',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Use IoT Devices in the PoS',
    'description': """
Allows to use in the Point of Sale the devices that are connected to an IoT Box.
Supported devices include payment terminals, receipt printers, scales and customer displays.
""",
    'data': [
        'views/pos_config_views.xml',
        'views/res_config_setting_views.xml',
        'views/pos_payment_method_views.xml',
        'views/pos_printer_views.xml',
    ],
    'depends': ['point_of_sale', 'iot'],
    'installable': True,
    'auto_install': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'OEEL-1',
    'assets': {
        'point_of_sale._assets_pos': [
            'iot/static/src/iot_longpolling.js',
            'iot/static/src/device_controller.js',
            'iot/static/src/iot_report_action.js',
            'iot/static/src/iot_connection_error_dialog.js',
            'pos_iot/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_iot/static/tests/tours/**/*',
        ],
        'point_of_sale.assets_qunit_tests': [
            'pos_iot/static/tests/unit/**/*',
        ],
    }
}
