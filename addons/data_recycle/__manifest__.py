# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Data Recycle',
    'version': '1.3',
    'category': 'Productivity/Data Cleaning',
    'summary': 'Find old records and archive/delete them',
    'description': """Find old records and archive/delete them""",
    'depends': ['mail'],
    'data': [
        'data/ir_cron_data.xml',
        'views/data_recycle_model_views.xml',
        'views/data_recycle_record_views.xml',
        'views/data_cleaning_menu.xml',
        'views/data_recycle_templates.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'data_recycle/static/src/views/*.js',
            'data_recycle/static/src/views/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
