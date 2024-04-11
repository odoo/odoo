# -*- coding: utf-8 -*-
{
    'name': 'Website Live Chat',
    'category': 'Hidden',
    'summary': 'Chat with your website visitors',
    'version': '1.0',
    'description': """
Allow website visitors to chat with the collaborators. This module also brings a feedback tool for the livechat and web pages to display your channel with its ratings on the website.
    """,
    'depends': ['website', 'im_livechat'],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/website_livechat.xml',
        'views/res_config_settings_views.xml',
        'views/im_livechat_chatbot_script_view.xml',
        'views/website_livechat_view.xml',
        'views/website_visitor_views.xml',
        'views/im_livechat_channel_add.xml',
        'security/ir.model.access.csv',
        'security/website_livechat.xml',
        'data/website_livechat_data.xml',
    ],
    'demo': [
        'data/website_livechat_chatbot_demo.xml',
    ],
    'assets': {
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
            'website_livechat/static/src/**/*',
            ('remove', 'website_livechat/static/src/scss/**/*'),
        ],
        'web.assets_unit_tests': [
            'website_livechat/static/tests/**/*',
            ('remove', 'website_livechat/static/tests/embed/**/*'),
            ('remove', 'website_livechat/static/tests/tours/**/*'),
        ],
        'im_livechat.embed_assets_unit_tests': [
            'website_livechat/static/tests/mock_server/**/*',
            'website_livechat/static/tests/website_livechat_test_helpers.js',
            'website_livechat/static/tests/embed/**/*',
        ],
        'web.assets_tests': [
            'website_livechat/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
