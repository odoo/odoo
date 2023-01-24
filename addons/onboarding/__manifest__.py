# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Onboarding Toolbox',
    'version': '1.2',
    'category': 'Hidden',
    'sequence': 9001,
    'description': """
This module allows to manage onboardings and their progress
================================================================================
    """,
    'depends': ['base'],
    'installable': True,
    'data': [
        'data/onboarding_data.xml',
        'views/onboarding_views.xml',
        'views/onboarding_templates.xml',
        'views/onboarding_menus.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'onboarding/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
