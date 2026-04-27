# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mail Enterprise',
    'category': 'Productivity/Discuss',
    'depends': ['mail', 'web_mobile'],
    'description': """
Bridge module for mail and enterprise
=====================================

Display a preview of the last chatter attachment in the form view for large
screen devices.
""",
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'mail_enterprise/static/src/core/common/**/*',
            'mail_enterprise/static/src/**/*',
        ],
        'web.assets_tests': [
            'mail_enterprise/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'mail_enterprise/static/tests/**/*',
        ],
    }
}
