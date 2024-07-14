# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Timer',
    'version': '1.0',
    'sequence': 24,
    'summary': 'Record time',
    'category': 'Services/Timesheets',
    'description': """
This module implements a timer.
==========================================

It adds a timer to a view for time recording purpose
    """,
    'depends': ['web', 'mail'],
    'data': [
        'security/timer_security.xml',
        'security/ir.model.access.csv',
        ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'timer/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'timer/static/tests/**/*',
        ],
    },
    'license': 'OEEL-1',
}
