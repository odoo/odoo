# -*- coding: utf-8 -*-
{
    'name' : 'Live Chat',
    'version': '1.0',
    'sequence': 210,
    'summary': 'Chat with your website visitors',
    'category': 'Website/Live Chat',
    'complexity': 'easy',
    'website': 'https://www.odoo.com/page/live-chat',
    'description':
        """
Live Chat Support
==========================

Allow to drop instant messaging widgets on any web page that will communicate
with the current server and dispatch visitors request amongst several live
chat operators.
Help your customers with this chat, and analyse their feedback.

        """,
    'data': [
        "security/im_livechat_channel_security.xml",
        "security/ir.model.access.csv",
        "data/mail_shortcode_data.xml",
        "data/mail_data.xml",
        "data/im_livechat_channel_data.xml",
        'data/digest_data.xml',
        "views/rating_views.xml",
        "views/mail_channel_views.xml",
        "views/im_livechat_channel_views.xml",
        "views/im_livechat_channel_templates.xml",
        "views/res_users_views.xml",
        "views/digest_views.xml",
        "report/im_livechat_report_channel_views.xml",
        "report/im_livechat_report_operator_views.xml"
    ],
    'demo': [
        "data/im_livechat_channel_demo.xml",
        'data/mail_shortcode_demo.xml',
    ],
    'depends': ["mail", "rating", "digest"],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'im_livechat/static/src/js/im_livechat_channel_form_view.js',
            'im_livechat/static/src/js/im_livechat_channel_form_controller.js',
            'im_livechat/static/src/bugfix/bugfix.js',
            'im_livechat/static/src/components/discuss/discuss.js',
            'im_livechat/static/src/components/discuss_sidebar/discuss_sidebar.js',
            'im_livechat/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js',
            'im_livechat/static/src/components/notification_list/notification_list.js',
            'im_livechat/static/src/components/thread_needaction_preview/thread_needaction_preview.js',
            'im_livechat/static/src/components/thread_preview/thread_preview.js',
            'im_livechat/static/src/models/messaging_initializer/messaging_initializer.js',
            'im_livechat/static/src/models/messaging_notification_handler/messaging_notification_handler.js',
            'im_livechat/static/src/models/partner/partner.js',
            'im_livechat/static/src/models/thread/thread.js',
            'im_livechat/static/src/widgets/discuss/discuss.js',
            'im_livechat/static/src/bugfix/bugfix.scss',
            'im_livechat/static/src/scss/im_livechat_history.scss',
            'im_livechat/static/src/scss/im_livechat_form.scss',
        ],
        'web.qunit_suite_tests': [
            'im_livechat/static/src/bugfix/bugfix_tests.js',
            'im_livechat/static/src/components/chat_window_manager/chat_window_manager_tests.js',
            'im_livechat/static/src/components/composer/composer_tests.js',
            'im_livechat/static/src/components/discuss/discuss_tests.js',
            'im_livechat/static/src/components/messaging_menu/messaging_menu_tests.js',
            'im_livechat/static/src/components/thread_icon/thread_icon_tests.js',
            'im_livechat/static/src/components/thread_textual_typing_status/thread_textual_typing_status_tests.js',
            'im_livechat/static/src/legacy/public_livechat.js',
            'im_livechat/static/tests/helpers/mock_models.js',
            'im_livechat/static/tests/helpers/mock_server.js',
        ],
        'web.assets_qweb': [
            'im_livechat/static/src/bugfix/bugfix.xml',
            'im_livechat/static/src/components/composer/composer.xml',
            'im_livechat/static/src/components/discuss_sidebar/discuss_sidebar.xml',
            'im_livechat/static/src/components/thread_icon/thread_icon.xml',
        ],
    }
}
