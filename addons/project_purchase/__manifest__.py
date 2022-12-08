# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Project Purchase",
    'version': '1.0',
    'summary': "Monitor purchase in project",
    'category': 'Services/Project',
    'depends': ['purchase', 'project'],
    'demo': [
        'data/project_purchase_demo.xml',
    ],
    'data': [
        'views/project_task_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
