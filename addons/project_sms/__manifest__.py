# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Project - SMS",
    'summary': 'Send text messages when project/task stage move',
    'description': "Send text messages when project/task stage move",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['project', 'sms'],
    'data': [
        'views/project_stage_views.xml',
        'views/project_task_type_views.xml',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
