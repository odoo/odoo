# -*- coding: utf-8 -*-
{
    'name': 'Website Live Chat',
    'category': 'Hidden',
    'summary': 'Chat with your website visitors',
    'version': '1.0',
    'description': "Allow website visitors to chat with the collaborators.",
    'depends': ['website', 'im_livechat'],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/website_livechat.xml',
        'views/res_config_settings_views.xml',
        'views/im_livechat_chatbot_script_view.xml',
        'views/website_visitor_views.xml',
        'views/im_livechat_channel_add.xml',
        'security/ir.model.access.csv',
        'data/website_livechat_data.xml',
    ],
    'demo': [
        'data/website_livechat_chatbot_demo.xml',
        'demo/im_livechat_session_11.xml',
    ],
    'assets': {
        "mail.assets_public": [
            "website_livechat/static/src/**/common/**/*",
        ],
        'website.assets_wysiwyg': [
            'website_livechat/static/src/scss/**/*',
        ],
        'website.assets_editor': [
            'website_livechat/static/src/js/**/*',
        ],
        'web.assets_frontend': [
            'website_livechat/static/src/patch/assets_frontend/website.scss',
        ],
        'web.assets_backend': [
            "website_livechat/static/src/**/common/**/*",
            'website_livechat/static/src/**/*',
            ('remove', 'website_livechat/static/src/scss/**/*'),
        ],
        'web.assets_unit_tests': [
            'website_livechat/static/tests/**/*',
            ('remove', 'website_livechat/static/tests/tours/**/*'),
        ],
        'web.assets_tests': [
            'website_livechat/static/tests/tours/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
