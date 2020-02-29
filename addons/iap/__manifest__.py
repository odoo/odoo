# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'In-App Purchases',
    'category': 'Tools',
    'summary': 'Basic models and helpers to support In-App purchases.',
    'description': """
This module provides standard tools (account model, context manager and helpers) to support In-App purchases inside Odoo.
""",
    'depends': ['web', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/assets.xml',
        'views/iap_views.xml',
        'views/res_config_settings.xml',
    ],
    'images': [
        'static/src/img/iap_logo.svg',
    ],
    'qweb': [
        'static/src/xml/iap_templates.xml',
    ],
    'auto_install': True,
}
