# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Resource Mail',
    'version': '1.0',
    'category': 'Hidden',
    'description': """Integrate features developped in Mail in use case involving resources instead of users""",
    'depends': ['resource', 'mail'],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'resource_mail/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'resource_mail/static/tests/**/*',
            ('remove', 'resource_mail/static/tests/legacy/**/*'),
        ],
        'web.qunit_suite_tests': [
            'resource_mail/static/tests/legacy/**/*',
        ],
    },
    'license': 'LGPL-3',
}
