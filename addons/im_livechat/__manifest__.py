{
    'name': 'Live Chat',
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
        'data/utm_data.xml',
        'views/chatbot_script_answer_views.xml',
        'views/chatbot_script_step_views.xml',
        'views/chatbot_script_views.xml',
        "views/discuss_channel_views.xml",
        "views/res_partner_views.xml",
        "views/im_livechat_channel_views.xml",
        "views/im_livechat_channel_templates.xml",
        "views/im_livechat_chatbot_templates.xml",
        "views/im_livechat_channel_config_views.xml",
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
    'depends': ["mail", "digest", "utm", "phone_validation"],
    'application': True,
    'assets': {
        'web.assets_frontend': [
            'web/static/src/views/fields/file_handler.*',
            'web/static/src/views/fields/formatters.js',
            ('include', 'im_livechat.assets_embed_core'),
            'im_livechat/static/src/embed/frontend/**/*',
        ],
        'web.assets_backend': [
            'im_livechat/static/src/js/colors_reset_button/*',
            'im_livechat/static/src/js/im_livechat_chatbot_steps_one2many.js',
            'im_livechat/static/src/views/**/*',
            ('remove', 'im_livechat/static/src/views/lazy/**/*'),
            'im_livechat/static/src/scss/im_livechat_history.scss',
            'im_livechat/static/src/scss/im_livechat_form.scss',
            'im_livechat/static/src/core/common/**/*',
            'im_livechat/static/src/core/public_web/**/*',
            'im_livechat/static/src/core/web/**/*',
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
        'web.assets_tests': [
            'im_livechat/static/tests/tours/**/*',
        ],
        'im_livechat.assets_embed_core': [
            'im_livechat/static/src/core/common/**/*',
            'im_livechat/static/src/embed/common/**/*',
        ],
        'im_livechat.assets_embed_external': [
            'im_livechat/static/src/embed/external/**/*',
        ],
        'im_livechat.assets_embed_cors': [
            'im_livechat/static/src/embed/cors/**/*',
        ],
        'im_livechat.embed_assets_unit_tests_setup': [
            ('remove', 'im_livechat/static/**'),
            ('include', 'im_livechat.assets_embed_external'),
            ('remove', 'im_livechat/static/src/embed/external/boot.js'),
            'im_livechat/static/tests/livechat_test_helpers.js',
            'im_livechat/static/tests/mock_server/**/*',
        ],
        "im_livechat.assets_livechat_support_tours": [
            "web_tour/static/src/js/**/*",
            "web/static/lib/hoot-dom/**/*",
            'web_tour/static/src/tour_utils.js',
            "web/static/tests/legacy/helpers/cleanup.js",
            "web/static/tests/legacy/helpers/utils.js",
            "im_livechat/static/tests/tours/support/*",
        ],
        'im_livechat.embed_assets_unit_tests': [
            'web/static/tests/_framework/**/*',
            'im_livechat/static/tests/embed/**/*',
        ],
        "mail.assets_public": [
            "im_livechat/static/src/core/common/**/*",
            "im_livechat/static/src/core/public_web/**/*",
        ],
        "portal.assets_chatter_helpers": [
            "im_livechat/static/src/core/common/**/*",
            ("remove", "im_livechat/static/src/core/common/**/*.scss"),
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
