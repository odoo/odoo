# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Internet of Things',
    'category': 'Tools',
    'summary': 'Basic models and helpers to support Internet of Things.',
    'description': """
This module provides management of your IoT boxes inside Odoo.
""",
    'depends': ['web'],
    'data': [
        'views/iot_views.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': False,
}
