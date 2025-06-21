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
    'depends': ['web'],
    'installable': True,
    'data': [
        'views/onboarding_templates.xml',
        'views/onboarding_views.xml',
        'views/onboarding_menus.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'onboarding/static/src/**/*',
            ("remove", "onboarding/static/src/scss/onboarding.variables.dark.scss"),
        ],
        "web.dark_mode_variables": [
            ('before', 'onboarding/static/src/scss/onboarding.variables.scss', 'onboarding/static/src/scss/onboarding.variables.dark.scss'),
        ],
        'web._assets_primary_variables': [
            'onboarding/static/src/scss/onboarding.variables.scss',
        ]
    },
    'license': 'LGPL-3',
}
