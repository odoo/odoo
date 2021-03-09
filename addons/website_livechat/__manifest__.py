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
            # inside .
            'mail/static/src/js/utils.js',
            # inside .
            'website_livechat/static/src/bugfix/public_bugfix.js',
            # inside .
            'im_livechat/static/src/legacy/public_livechat.js',
            # inside .
            'website_livechat/static/src/legacy/public_livechat.js',
            # inside .
            'im_livechat/static/src/legacy/public_livechat.scss',
            # inside .
            'website_livechat/static/src/bugfix/public_bugfix.scss',
        ],
        'website.assets_editor': [
            # inside .
            'website_livechat/static/src/js/website_livechat.editor.js',
        ],
        'web.assets_backend': [
            # after script[last()]
            'website_livechat/static/src/bugfix/bugfix.js',
            # after script[last()]
            'website_livechat/static/src/components/discuss/discuss.js',
            # after script[last()]
            'website_livechat/static/src/components/visitor_banner/visitor_banner.js',
            # after script[last()]
            'website_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js',
            # after script[last()]
            'website_livechat/static/src/models/thread/thread.js',
            # after script[last()]
            'website_livechat/static/src/models/visitor/visitor.js',
            # after link[last()]
            'website_livechat/static/src/bugfix/bugfix.scss',
            # after link[last()]
            'website_livechat/static/src/components/visitor_banner/visitor_banner.scss',
        ],
        'web.assets_tests': [
            # inside .
            'website_livechat/static/tests/tours/website_livechat_common.js',
            # inside .
            'website_livechat/static/tests/tours/website_livechat_rating.js',
            # inside .
            'website_livechat/static/tests/tours/website_livechat_request.js',
        ],
        'web.qunit_suite_tests': [
            # inside .
            'website_livechat/static/src/bugfix/bugfix_tests.js',
            # inside .
            'website_livechat/static/src/components/discuss/discuss_tests.js',
            # inside .
            'website_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler_tests.js',
            # inside .
            'website_livechat/static/tests/helpers/mock_models.js',
            # inside .
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
