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
    'application': False,
    'auto_install': True,
    'data': [
        'views/website_livechat.xml',
        'views/res_config_settings_views.xml',
        'views/website_livechat_view.xml',
        'views/website_visitor_views.xml',
        'security/ir.model.access.csv',
        'security/website_livechat.xml',
        'data/website_livechat_data.xml',
    ],
    'assets': {
        'mail.assets_discuss_public': [
            'website_livechat/static/src/components/*/*',
            'website_livechat/static/src/models/*/*.js',
        ],
        'web.assets_frontend': [
            'mail/static/src/js/utils.js',
            'im_livechat/static/src/legacy/public_livechat.js',
            'website_livechat/static/src/legacy/public_livechat.js',
            'im_livechat/static/src/legacy/public_livechat.scss',
            'website_livechat/static/src/legacy/public_livechat.scss',
        ],
        'website.assets_editor': [
            'website_livechat/static/src/js/**/*',
        ],
        'web.assets_backend': [
            'website_livechat/static/src/components/*/*.js',
            'website_livechat/static/src/components/*/*.scss',
            'website_livechat/static/src/models/*/*.js',
        ],
        'web.assets_tests': [
            'website_livechat/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'website_livechat/static/src/components/*/tests/*.js',
            'website_livechat/static/src/models/*/tests/*.js',
            'website_livechat/static/tests/helpers/mock_models.js',
            'website_livechat/static/tests/helpers/mock_server.js',
        ],
        'web.assets_qweb': [
            'website_livechat/static/src/components/*/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
