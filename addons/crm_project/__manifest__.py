# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Lead to Tasks',
    'summary': 'Create Tasks from Leads',
    'sequence': '19',
    'category': 'Project',
    'complexity': 'easy',
    'description': """
Lead to Tasks
=============

Link module to map leads to tasks
        """,
    'data': [
        'security/ir.model.access.csv',
        'wizard/crm_lead_convert2task_views.xml',
        'views/crm_lead_views.xml'
    ],
    'depends': ['crm', 'project'],
}
