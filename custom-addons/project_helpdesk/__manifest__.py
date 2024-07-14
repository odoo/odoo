# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Helpdesk',
    'version': '1.0',
    'category': 'Services',
    'summary': 'Project helpdesk',
    'description': 'Bridge created to convert tickets to tasks and tasks to tickets',
    'depends': ['project_enterprise', 'helpdesk'],
    'data': [
        'security/ir.model.access.csv',
        'views/helpdesk_views.xml',
        'views/project_views.xml',
        'wizard/helpdesk_ticket_convert_to_task_wizard_views.xml',
        'wizard/project_task_convert_to_ticket_wizard_views.xml',
    ],
    'demo': [
        'data/project_helpdesk_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
