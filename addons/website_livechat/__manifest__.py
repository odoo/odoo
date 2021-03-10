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
        'web.assets_frontend': [
            'mail/static/src/js/utils.js',
            'website_livechat/static/src/bugfix/public_bugfix.js',
            'im_livechat/static/src/legacy/public_livechat.js',
            'website_livechat/static/src/legacy/public_livechat.js',
            'im_livechat/static/src/legacy/public_livechat.scss',
            'website_livechat/static/src/bugfix/public_bugfix.scss',
        ],
        'website.assets_editor': [
            'website_livechat/static/src/js/**/*',
        ],
        'web.assets_backend': [
            'website_livechat/static/src/bugfix/bugfix.js',
            'website_livechat/static/src/components/discuss/discuss.js',
            'website_livechat/static/src/components/visitor_banner/visitor_banner.js',
            'website_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js',
            'website_livechat/static/src/models/thread/thread.js',
            'website_livechat/static/src/models/visitor/visitor.js',
            'website_livechat/static/src/bugfix/bugfix.scss',
            'website_livechat/static/src/components/visitor_banner/visitor_banner.scss',
        ],
        'web.assets_tests': [
            'website_livechat/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'website_livechat/static/src/bugfix/bugfix_tests.js',
            'website_livechat/static/src/components/discuss/discuss_tests.js',
            'website_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler_tests.js',
            'website_livechat/static/tests/helpers/mock_models.js',
            'website_livechat/static/tests/helpers/mock_server.js',
        ],
        'web.assets_qweb': [
            'website_livechat/static/src/bugfix/bugfix.xml',
            'website_livechat/static/src/bugfix/public_bugfix.xml',
            'website_livechat/static/src/components/discuss/discuss.xml',
            'website_livechat/static/src/components/visitor_banner/visitor_banner.xml',
        ],
    }
}
