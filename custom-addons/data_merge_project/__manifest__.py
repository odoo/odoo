# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Merge action',
    'version': '1.0',
    'category': 'Productivity/Data Cleaning',
    'summary': 'Add Merge action in contextual menu of project task and tag models.',
    'description': """Add Merge action in contextual menu of project task and tag models.""",
    'depends': ['data_merge', 'project'],
    'data': [
        'data/ir_model_data.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
