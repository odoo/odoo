# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Onboarding toolbox',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module handles onboarding progress
================================================================================

Shows you a list of applications features to install from.

    """,
    'depends': ['base'],
    'installable': True,
    'auto_install': True,
    'data': [
        'data/base_onboarding_data.xml',
        'views/base_onboarding_views.xml',
        'views/base_onboarding_menus.xml',
        'security/ir.model.access.csv',
    ],

    'license': 'LGPL-3',
}
