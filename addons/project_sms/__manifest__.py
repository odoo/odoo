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
        'security/ir.model.access.csv',
        'security/project_sms_security.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
