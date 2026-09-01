# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Task Stage Notification via SMS',
    'summary': 'Send text messages when project/task stage move',
    'description': "Automatically send an SMS to your customers when a task reaches a specific stage of the project.",
    'category': 'Services/Project',
    'version': '1.1',
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
