# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Deduplication',
    'version': '1.0',
    'category': 'Productivity/Data Cleaning',
    'summary': 'Find duplicate records and merge them',
    'description': """Find duplicate records and merge them""",
    'depends': ['data_cleaning', 'crm'],
    'data': [
        'data/data_merge_data.xml',
        'data/ir_model_data.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
