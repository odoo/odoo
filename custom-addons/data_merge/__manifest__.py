# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Data Cleaning (merge)',
    'version': '1.3',
    'category': 'Productivity/Data Cleaning',
    'summary': 'Find duplicate records and merge them',
    'description': """Find duplicate records and merge them""",
    'depends': ['mail', 'data_cleaning'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/data_merge_rule_views.xml',
        'views/data_merge_model_views.xml',
        'views/data_merge_record_views.xml',
        'views/data_merge_views.xml',
        'views/ir_model_views.xml',
        'data/mail_templates.xml',
        'data/data_merge_cron.xml',
        'data/data_merge_data.xml',
        'data/ir_model_data.xml',
    ],
    'auto_install': True,
    'installable': True,
    'post_init_hook': 'post_init',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_backend': [
            'data_merge/static/src/views/*.js',
            'data_merge/static/src/views/*.xml',
        ],
        'web.qunit_suite_tests': [
            'data_merge/static/tests/**/*.js',
        ],
    },
    'license': 'OEEL-1',
}
