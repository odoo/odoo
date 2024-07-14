# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Internet of Things',
    'category': 'Internet of Things (IoT)',
    'sequence': 250,
    'summary': 'Basic models and helpers to support Internet of Things.',
    'description': """
This module provides management of your IoT Boxes inside Odoo.
""",
    'depends': ['mail','web'],
    'data': [
        'wizard/add_iot_box_views.xml',
        'wizard/select_printers_views.xml',
        'security/ir.model.access.csv',
        'security/iot_security.xml',
        'views/iot_views.xml',
    ],
    'demo': [
        'data/iot_demo.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'iot/static/src/**/*',
        ],
        'web.tests_assets': [
            'iot/static/tests/helpers/**/*.js',
        ],
    }
}
