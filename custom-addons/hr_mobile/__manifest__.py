# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employees in Mobile',
    'category': 'Hidden',
    'summary': 'Employees in Mobile',
    'version': '1.0',
    'description': """ """,
    'depends': ['hr', 'web_mobile'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'hr_mobile/static/src/**/*',
        ],
        'web.qunit_mobile_suite_tests': [
            'hr_mobile/static/tests/**/*',
        ],
    }
}
