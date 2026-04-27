# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Quality Steps with IoT',
    'category': 'Manufacturing/Internet of Things (IoT)',
    'summary': 'Quality steps and IoT devices',
    'description': """
This module provides the link between quality steps and IoT devices. 
""",
    'depends': ['iot', 'quality'],
    'data': [
        'views/iot_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'quality_iot/static/src/**/*',
        ],
    }
}
