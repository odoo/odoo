# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test API',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """A module to test the API.""",
    'depends': ['base', 'web', 'web_tour'],
    'installable': True,
    'auto_install': False,
    'data': [
        'security/ir.model.access.csv',
        'security/test_new_api_security.xml',
        'views/test_new_api_views.xml',
        'views/test_new_api_templates.xml',
        'data/test_new_api_data.xml',
    ],
    'demo': [
    ],
    'license': 'LGPL-3',
}
