# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'IoT Base',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
Base tools required by all IoT related modules.
===============================================
""",
    'depends': ['web'],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'iot_base/static/src/network_utils/*',
            'iot_base/static/src/device_controller.js',
        ],
    },
}
