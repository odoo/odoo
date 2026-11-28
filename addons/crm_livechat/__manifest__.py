# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM Livechat',
    'category': 'Sales/CRM',
    'summary': 'Create lead from livechat conversation',
    'data': [
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
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': {
            'crm_livechat/static/src/core/**/*',
        },
        'web.assets_unit_tests': [
            'crm_livechat/static/tests/**/*',
            ("remove", "crm_livechat/static/tests/tours/**/*"),
        ],
        "im_livechat.assets_livechat_support_tours": [
            "crm_livechat/static/tests/tours/support/*",
        ],
        'im_livechat.embed_assets_unit_tests_setup': [
            ('remove', 'crm_livechat/static/src/core/web/**/*'),
        ],
    },
}
