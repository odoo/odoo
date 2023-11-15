# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Task Stage Notification via SMS',
    'summary': 'Automatically send an SMS text message to your customers when a task reaches a specific stage of the project.',
    'description': "Automatically send an SMS text message to your customers when a task reaches a specific stage of the project.",
    'category': 'Services/Project',
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
