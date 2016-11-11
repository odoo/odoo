# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pad on tasks',
    'category': 'Project',
    'description': """
This module adds a PAD in all project form views.
=================================================
    """,
    'website': 'https://www.odoo.com/page/project-management',
    'depends': [
        'project',
        'pad'
    ],
    'data': [
        'views/project_config_settings_views.xml',
        'views/project_task.xml'
    ],
    'auto_install': True,
}
