# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Self Order IoT',
    'version': '1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'IoT in PoS Kiosk',
    'depends': ['pos_iot', 'pos_self_order'],
    'auto_install': True,
    "data": [
        "views/iot_views.xml",
    ],
    "demo": [
        "demo/iot_demo.xml",
    ],
    'assets': {
        'pos_self_order.assets': [
            'web/static/lib/jquery/jquery.js',
            'iot/static/src/iot_longpolling.js',
            'iot/static/src/iot_connection_error_dialog.js',
            'iot/static/src/device_controller.js',
            'pos_iot/static/src/app/iot_printer.js',
            'pos_self_order_iot/static/src/overrides/models/*',
        ],
        'web.assets_backend': [
            'pos_self_order_iot/static/src/webclient/actions/*',
            'pos_self_order_iot/static/src/views/*',
        ],
    },
    'license': 'OEEL-1',
}
