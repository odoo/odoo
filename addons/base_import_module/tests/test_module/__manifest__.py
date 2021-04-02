# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Module',
    'category': 'Website/Website',
    'summary': 'Custom',
    'version': '1.0',
    'description': """
        Test
        """,
    'depends': ['website'],
    'data': [
        'test.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'test_module/static/src/js/test.js'
        ]
    },
    'installable': True,
    'application': True,
}
