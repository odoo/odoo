# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Monster Integration',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Monster integration
==========================
Post paid jobs automatically to monster

    """,
    'depends': ['hr_recruitment', 'hr_recruitment_integration'],
    'data': [
        'views/res_config_settings_views.xml',
        'wizard/hr_recruitment_post_job_views.xml'
    ],
    'installable': True,
    'license': 'LGPL-3',
}
