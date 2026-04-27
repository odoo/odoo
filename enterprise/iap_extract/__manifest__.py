# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Iap Extract',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'summary': 'Common module for requesting data from the extract server',
    'depends': ['base', 'iap', 'mail', 'iap_mail'],
    'data': [
        'data/config_parameter_endpoint.xml',
        'data/iap_service_data.xml',
        'data/mail_template_data.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'iap_extract/static/src/components/**/*',
        ]
    }
}
