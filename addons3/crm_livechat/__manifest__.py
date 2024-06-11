# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Livechat',
    'category': 'Sales/CRM',
    'summary': 'Create lead from livechat conversation',
    'data': [
        'data/utm_data.xml',
        'data/crm_livechat_chatbot_data.xml',
        'views/chatbot_script_views.xml',
        'views/chatbot_script_step_views.xml',
    ],
    'depends': [
        'crm',
        'im_livechat'
    ],
    'description': 'Create new lead with using /lead command in the channel',
    'auto_install': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': {
            'crm_livechat/static/src/core/*',
        },
        'web.qunit_suite_tests': [
            'crm_livechat/static/tests/**/*.js',
        ],
    },
}
