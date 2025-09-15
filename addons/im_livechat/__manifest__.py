{
    'name': 'Live Chat',
    'version': '1.0',
    'sequence': 210,
    'summary': 'Chat with your website visitors',
    'category': 'Website/Live Chat',
    'website': 'https://www.odoo.com/app/live-chat',
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
        "data/mail_templates.xml",
        "data/im_livechat_channel_data.xml",
        "data/im_livechat_chatbot_data.xml",
        'data/digest_data.xml',
        'views/chatbot_script_answer_views.xml',
        'views/chatbot_script_step_views.xml',
        'views/chatbot_script_views.xml',
        "views/discuss_channel_views.xml",
        "views/res_partner_views.xml",
        "views/im_livechat_conversation_tag_views.xml",
        "views/im_livechat_channel_views.xml",
        "views/im_livechat_channel_templates.xml",
        "views/im_livechat_chatbot_templates.xml",
        "views/im_livechat_expertise_views.xml",
        "views/im_livechat_channel_member_history_views.xml",
        "views/res_users_views.xml",
        "views/digest_views.xml",
        "views/webclient_templates.xml",
        "report/im_livechat_report_channel_views.xml",
        "report/im_livechat_conversation_report.xml",
    ],
    'demo': [
        "demo/im_livechat_channel/im_livechat_channel.xml",
        "demo/im_livechat_channel/im_livechat_chatbot.xml",
        "demo/im_livechat_channel/im_livechat_chatbot_session_1.xml",
        "demo/im_livechat_channel/im_livechat_chatbot_session_2.xml",
        "demo/im_livechat_channel/im_livechat_chatbot_session_3.xml",
        "demo/im_livechat_channel/im_livechat_session_1.xml",
        "demo/im_livechat_channel/im_livechat_session_2.xml",
        "demo/im_livechat_channel/im_livechat_session_3.xml",
        "demo/im_livechat_channel/im_livechat_session_4.xml",
        "demo/im_livechat_channel/im_livechat_session_5.xml",
        "demo/im_livechat_channel/im_livechat_session_6.xml",
        "demo/im_livechat_channel/im_livechat_session_7.xml",
        "demo/im_livechat_channel/im_livechat_session_8.xml",
        "demo/im_livechat_channel/im_livechat_session_9.xml",
        "demo/im_livechat_channel/im_livechat_session_10.xml",
        "demo/im_livechat_channel/im_livechat_session_11.xml",
        "demo/im_livechat_channel/im_livechat_session_12.xml",
        "demo/im_livechat_channel/im_livechat_session_13.xml",
        "demo/im_livechat_channel/im_livechat_session_14.xml",
        "demo/im_livechat_channel/im_livechat_session_15.xml",
        "demo/im_livechat_channel/im_livechat_support_bot.xml",
        "demo/im_livechat_channel/im_livechat_support_bot_session_1.xml",
        "demo/im_livechat_channel/im_livechat_support_bot_session_2.xml",
        "demo/im_livechat_channel/im_livechat_support_bot_session_3.xml",
        "demo/im_livechat_channel/im_livechat_support_bot_session_4.xml",
        "demo/im_livechat_channel/im_livechat_support_bot_session_5.xml",
        "demo/im_livechat_channel/im_livechat_support_bot_session_6.xml",
        "demo/im_livechat_channel/im_livechat_support_bot_session_7.xml",
    ],
    'depends': ["mail", "rating", "digest", "utm"],
    'installable': True,
    'application': True,
    'assets': {
        "discuss.assets_core_common": [
            "im_livechat/static/src/discuss/core/common/**/*",
        ],
        "discuss.assets_core_public_web": [
            "im_livechat/static/src/discuss/core/public_web/**/*",
        ],
        "discuss.assets_core_web": [
            "im_livechat/static/src/discuss/core/web/**/*",
        ],
        "discuss.assets_feature_common": [
            "im_livechat/static/src/discuss/**/common/**/*",
        ],
        "discuss.assets_feature_web": [
            "im_livechat/static/src/discuss/**/web/**/*",
        ],
        "im_livechat.assets_core_common": [],
        "im_livechat.assets_core_cors": [
            "im_livechat/static/src/core/cors/**/*",
        ],
        "im_livechat.assets_core_cors_external": [
            "im_livechat/static/src/core/cors_external/**/*",
        ],
        "im_livechat.assets_core_cors_external_frontend": [
            # path should be changed to core/cors_external_frontend
            'im_livechat/static/src/embed/common/**/*',
        ],
        "im_livechat.assets_core_frontend": [
            "im_livechat/static/src/core/frontend/**/*",
        ],
        "im_livechat.assets_core_web": [],
        "mail.assets_public": [
            ("include", "im_livechat.assets_core_common"),
        ],
        "portal.assets_chatter_helpers_no_style": [
            ("remove", "im_livechat/static/src/**/*.scss"),
        ],
        # top level bundle used to embed on the current website (same origin)
        'web.assets_frontend': [
            'web/static/src/views/fields/file_handler.*',
            'web/static/src/views/fields/formatters.js',
            ("include", "im_livechat.assets_discuss_cors_external_frontend"),
            ("include", "im_livechat.assets_core_common"),
            ("include", "im_livechat.assets_core_cors_external_frontend"),
            ("include", "im_livechat.assets_core_frontend"),
        ],
        'web.assets_backend': [
            ("include", "im_livechat.assets_core_common"),
            ("include", "im_livechat.assets_core_web"),
            'im_livechat/static/src/js/colors_reset_button/*',
            'im_livechat/static/src/js/im_livechat_chatbot_steps_one2many.js',
            'im_livechat/static/src/js/im_livechat_chatbot_script_answers_m2m.js',
            'im_livechat/static/src/views/**/*',
            ('remove', 'im_livechat/static/src/views/lazy/**/*'),
            'im_livechat/static/src/scss/im_livechat_history.scss',
            'im_livechat/static/src/scss/im_livechat_form.scss',
            ('remove', 'im_livechat/static/src/**/*.dark.scss'),
        ],
        'web.assets_backend_lazy': [
            "im_livechat/static/src/views/lazy/**/*",
        ],
        "web.assets_web_dark": [
            'im_livechat/static/src/**/*.dark.scss',
        ],
        'web.assets_unit_tests': [
            'im_livechat/static/tests/**/*',
            ('remove', 'im_livechat/static/tests/embed/**/*'),
            ('remove', 'im_livechat/static/tests/tours/**/*'),
        ],
        'im_livechat.qunit_embed_suite': [
            'im_livechat/static/tests/embed/**/*',
        ],
        'web.assets_tests': [
            'im_livechat/static/tests/tours/**/*',
        ],
        # Technical bundle common to current website, support page, and external websites. This
        # bundles contains the minimal discuss dependencies necessary to run the live chat code in
        # contexts where the discuss code is not already present, but it should not contain the live
        # chat code directly.
        "im_livechat.assets_discuss_cors_external_frontend": [
            ("include", "html_editor.assets_editor"),
            ("include", "mail.assets_core_common"),
            ("include", "mail.assets_feature_common"),
            ("include", "discuss.assets_core_common"),
            ("include", "discuss.assets_feature_common"),
        ],
        # Technical bundle common to embed on support page and on external website. This bundle
        # contains the minimal framework dependencies necessary to run the live chat code in embed
        # contexts, but it should not contain the discuss nor the live chat code directly.
        "im_livechat.assets_framework_cors_external": [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            ('include', 'web._assets_bootstrap_backend'),
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/scss/ui.scss',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/animation.scss',
            'web/static/lib/odoo_ui_icons/style.css',
            'web/static/src/webclient/webclient.scss',
            ('include', 'web._assets_core'),
            'web/static/src/views/fields/formatters.js',
            'web/static/src/views/fields/file_handler.*',
            'web/static/src/scss/mimetypes.scss',
            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            'bus/static/src/workers/*.js',
            ('remove', 'bus/static/src/workers/bus_worker_script.js'),
            ('remove', 'bus/static/src/outdated_page_watcher_service.js'),
            ('remove', 'bus/static/src/services/assets_watchdog_service.js'),
            ('remove', 'bus/static/src/simple_notification_service.js'),
        ],
        # top level bundle used to embed on the support page (same origin)
        'im_livechat.assets_embed_external': [
            ("include", "im_livechat.assets_framework_cors_external"),
            ("include", "im_livechat.assets_discuss_cors_external_frontend"),
            ("include", "im_livechat.assets_core_cors_external_frontend"),
            ("include", "im_livechat.assets_core_cors_external"),
        ],
        # top level bundle used to embed on an external website (different origin)
        'im_livechat.assets_embed_cors': [
            ("include", "im_livechat.assets_framework_cors_external"),
            ("include", "im_livechat.assets_discuss_cors_external_frontend"),
            ("include", "im_livechat.assets_core_cors_external_frontend"),
            ("include", "im_livechat.assets_core_cors_external"),
            ("include", "im_livechat.assets_core_cors"),
        ],
        'im_livechat.embed_assets_unit_tests_setup': [
            ('include', 'web.assets_unit_tests_setup'),
            ('remove', 'im_livechat/static/**'),
            ('include', 'im_livechat.assets_embed_external'),
            ('remove', 'im_livechat/static/src/core/cors_external/boot.js'),
            'web/static/src/core/browser/title_service.js',
            'web/static/tests/web_test_helpers.js',
            'bus/static/tests/bus_test_helpers.js',
            'mail/static/tests/mail_test_helpers.js',
            'mail/static/tests/mail_test_helpers_contains.js',
            'im_livechat/static/tests/livechat_test_helpers.js',
            'bus/static/tests/mock_server/**/*',
            'mail/static/tests/mock_server/**/*',
            'rating/static/tests/mock_server/**/*',
            'im_livechat/static/tests/mock_server/**/*',
            'bus/static/tests/mock_*.js',
        ],
        "im_livechat.assets_livechat_support_tours": [
            "web_tour/static/src/js/**/*",
            "web/static/lib/hoot-dom/**/*",
            'web_tour/static/src/tour_utils.js',
            "web/static/tests/legacy/helpers/cleanup.js",
            "web/static/tests/legacy/helpers/utils.js",
            "web/static/tests/legacy/utils.js",
            "im_livechat/static/tests/tours/support/*",
        ],
        'im_livechat.embed_assets_unit_tests': [
            'web/static/tests/_framework/**/*',
            'im_livechat/static/tests/embed/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
