# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Resource',
    'version': '1.1',
    'category': 'Hidden',
    'description': """
Module for resource management.
===============================

A resource represent something that can be scheduled (a developer on a task or a
work center on manufacturing orders). This module manages a resource calendar
associated to every resource. It also manages the leaves of every resource.
    """,
    'depends': ['base', 'web'],
    'data': [
        'data/resource_data.xml',
        'security/ir.model.access.csv',
        'security/resource_security.xml',
        'views/resource_resource_views.xml',
        'views/resource_calendar_leaves_views.xml',
        'views/resource_calendar_attendance_views.xml',
        'views/resource_calendar_views.xml',
        'views/menuitems.xml',
    ],
    'demo': [
        'data/resource_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'resource/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'resource/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
