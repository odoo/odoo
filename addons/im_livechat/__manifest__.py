# -*- coding: utf-8 -*-
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
        "data/discuss_shortcode_data.xml",
        "data/mail_templates.xml",
        "data/im_livechat_channel_data.xml",
        "data/im_livechat_chatbot_data.xml",
        'data/digest_data.xml',
        'views/chatbot_script_answer_views.xml',
        'views/chatbot_script_step_views.xml',
        'views/chatbot_script_views.xml',
        "views/rating_rating_views.xml",
        "views/discuss_channel_views.xml",
        "views/im_livechat_channel_views.xml",
        "views/im_livechat_channel_templates.xml",
        "views/im_livechat_chatbot_templates.xml",
        "views/res_users_views.xml",
        "views/digest_views.xml",
        "views/webclient_templates.xml",
        "report/im_livechat_report_channel_views.xml",
        "report/im_livechat_report_operator_views.xml"
    ],
    'demo': [
        "demo/im_livechat_channel/im_livechat_channel.xml",
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
        "demo/discuss_shortcode/discuss_shortcode_demo.xml",
    ],
    'depends': ["mail", "rating", "digest", "utm"],
    'installable': True,
    'application': True,
    'assets': {
        'web._assets_primary_variables': [
            'im_livechat/static/src/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'web/static/src/views/fields/file_handler.*',
            'web/static/src/views/fields/formatters.js',
            ('include', 'im_livechat.assets_embed_core'),
            'im_livechat/static/src/embed/frontend/**/*',
        ],
        'web.assets_backend': [
            'im_livechat/static/src/js/colors_reset_button/*',
            'im_livechat/static/src/js/im_livechat_chatbot_steps_one2many.js',
            'im_livechat/static/src/js/im_livechat_chatbot_script_answers_m2m.js',
            'im_livechat/static/src/views/**/*',
            'im_livechat/static/src/scss/im_livechat_history.scss',
            'im_livechat/static/src/scss/im_livechat_form.scss',
            'im_livechat/static/src/core/common/**/*',
            'im_livechat/static/src/core/web/**/*',
        ],
        'web.tests_assets': [
            'im_livechat/static/tests/helpers/**/*.js',
        ],
        'web.qunit_suite_tests': [
            'im_livechat/static/tests/**/*',
            ('remove', 'im_livechat/static/tests/embed/**/*'),
            ('remove', 'im_livechat/static/tests/tours/**/*'),
            ('remove', 'im_livechat/static/tests/helpers/**/*.js'),
        ],
        'web.assets_tests': [
            'im_livechat/static/tests/tours/**/*',
        ],
        'im_livechat.assets_embed_core': [
            'web/static/lib/odoo_ui_icons/style.css',
            'web/static/src/scss/ui.scss',
            'mail/static/src/core/common/**/*',
            'mail/static/src/discuss/core/common/*',
            'mail/static/src/discuss/call/common/**',
            'mail/static/src/discuss/typing/**/*',
            'mail/static/src/utils/common/**/*',
            ('remove', 'mail/static/src/**/*.dark.scss'),
            'im_livechat/static/src/core/common/**/*',
            'im_livechat/static/src/embed/common/**/*',
        ],
        'im_livechat.assets_embed_external': [
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'im_livechat/static/src/embed/common/scss/bootstrap_overridden.scss',
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_backend'),
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/webclient/webclient.scss',
            ('include', 'web._assets_core'),
            'web/static/src/libs/pdfjs.js',
            'web/static/src/views/fields/formatters.js',
            'web/static/src/views/fields/file_handler.*',
            'web/static/src/scss/mimetypes.scss',
            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            'bus/static/src/workers/websocket_worker.js',
            'bus/static/src/workers/websocket_worker_utils.js',
            ('remove', 'bus/static/src/services/assets_watchdog_service.js'),
            ('remove', 'bus/static/src/simple_notification_service.js'),
            ('include', 'im_livechat.assets_embed_core'),
            'im_livechat/static/src/embed/external/**/*',
        ],
        'im_livechat.assets_embed_cors': [
            ('include', 'im_livechat.assets_embed_external'),
            'im_livechat/static/src/embed/cors/**/*',
        ],
        'im_livechat.embed_test_assets': [
            ('include', 'web.tests_assets'),
            ('remove', 'web/static/tests/mock_server_tests.js'),
            ('remove', 'im_livechat/static/**'),
            'im_livechat/static/tests/helpers/**',
            ('include', 'im_livechat.assets_embed_core'),
        ],
        'im_livechat.qunit_embed_suite': [
            'im_livechat/static/tests/embed/**/*',
        ],
    },
    'license': 'LGPL-3',
}
