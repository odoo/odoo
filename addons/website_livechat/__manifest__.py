# -*- coding: utf-8 -*-
{
    'name': 'Website Live Chat',
    'category': 'Website/Live Chat',
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
        "im_livechat.assets_embed_core": [
            "website/static/src/**/common/**/*",
            "website_livechat/static/src/**/common/**/*",
        ],
        'im_livechat.embed_assets_unit_tests_setup': [
            ('remove', 'website_livechat/static/**'),
            "web/static/tests/public/helpers.js",
            "website/static/tests/helpers.js",
            'website_livechat/static/tests/website_livechat_test_helpers.js',
            "website/static/tests/mock_server/**/*",
            "website_livechat/static/tests/mock_server/**/*",
        ],
        "mail.assets_public": [
            "website_livechat/static/src/**/common/**/*",
        ],
        'website.assets_wysiwyg': [
            "website/static/src/**/common/**/*",
        ],
        'website.assets_editor': [
            'website_livechat/static/src/js/**/*',
        ],
        'web.assets_frontend': [
            "website_livechat/static/src/**/common/**/*",
            'website_livechat/static/src/**/frontend/**/*',
        ],
        'web.assets_backend': [
            "website_livechat/static/src/**/common/**/*",
            'website_livechat/static/src/**/*',
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
