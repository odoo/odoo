# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test API',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'description': """A module to test the API.""",
    'depends': ['base', 'web', 'web_tour'],
    'installable': True,
    'data': [
        'views/test_new_api_views.xml',
        'data/test_new_api_data.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_tests': [
            # inside .
            'test_new_api/static/tests/tours/constraint.js',
            # inside .
            'test_new_api/static/tests/tours/x2many.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
