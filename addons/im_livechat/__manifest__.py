{
    "name": "Live Chat",
    "version": "1.0",
    "category": "Website/Live Chat",
    "sequence": 210,
    "summary": "Chat with your website visitors",
    "description": """
Live Chat Support
==========================

Allow to drop instant messaging widgets on any web page that will communicate
with the current server and dispatch visitors request amongst several live
chat operators.
Help your customers with this chat, and analyse their feedback.

        """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/live-chat",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "rating",
        "digest",
        "utm",
    ],
    "data": [
        "security/im_livechat_channel_security.xml",
        "security/ir.model.access.csv",
        "data/mail_templates.xml",
        "data/im_livechat_channel_data.xml",
        "data/im_livechat_chatbot_data.xml",
        "data/digest_data.xml",
        "views/chatbot_script_answer_views.xml",
        "views/chatbot_script_step_views.xml",
        "views/chatbot_script_views.xml",
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
        "reports/im_livechat_report_channel_views.xml",
        "reports/im_livechat_conversation_report.xml",
        "views/im_livechat_menus.xml",
    ],
    "demo": [
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
    "assets": {
        "web.assets_frontend": [
            (
                "include",
                "im_livechat.assets_embed_core",
            ),
            (
                "remove",
                "web/static/src/core/browser/title_service.js",
            ),
            "im_livechat/static/src/embed/frontend/**/*",
        ],
        "web.assets_backend": [
            "im_livechat/static/src/js/colors_reset_button/*",
            "im_livechat/static/src/js/im_livechat_chatbot_steps_one2many.js",
            "im_livechat/static/src/js/im_livechat_chatbot_script_answers_m2m.js",
            "im_livechat/static/src/views/**/*",
            "im_livechat/static/src/scss/im_livechat_history.scss",
            "im_livechat/static/src/scss/im_livechat_form.scss",
            "im_livechat/static/src/core/common/**/*",
            "im_livechat/static/src/core/public_web/**/*",
            "im_livechat/static/src/core/web/**/*",
        ],
        "web.assets_unit_tests": [
            "im_livechat/static/tests/**/*",
            (
                "remove",
                "im_livechat/static/tests/embed/**/*",
            ),
            (
                "remove",
                "im_livechat/static/tests/tours/**/*",
            ),
        ],
        "web.assets_tests": [
            "im_livechat/static/tests/tours/**/*",
        ],
        "im_livechat.assets_embed_core": [
            (
                "include",
                "html_editor._assets_editor",
            ),
            (
                "include",
                "mail.assets_core_common",
            ),
            (
                "include",
                "mail.assets_discuss_core_common",
            ),
            (
                "include",
                "mail.assets_discuss_call_common",
            ),
            (
                "include",
                "mail.assets_discuss_typing_common",
            ),
            "rating/static/src/core/common/**/*",
            "im_livechat/static/src/core/common/**/*",
            "im_livechat/static/src/embed/common/**/*",
        ],
        "im_livechat.assets_embed_external": [
            (
                "include",
                "web._assets_helpers",
            ),
            (
                "include",
                "web._assets_backend_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            (
                "include",
                "web._assets_bootstrap_backend",
            ),
            "web/static/src/scss/bootstrap_overridden.scss",
            "web/static/src/scss/tokens.scss",
            "web/static/src/scss/ui.scss",
            "web/static/src/libs/fontawesome7/css/fontawesome.css",
            "web/static/src/libs/fontawesome7/css/solid.css",
            "web/static/src/libs/fontawesome7/css/regular.css",
            "web/static/src/libs/fontawesome7/css/brands.css",
            "web/static/src/scss/animation.scss",
            "web/static/lib/odoo_ui_icons/style.css",
            "web/static/src/webclient/webclient.scss",
            (
                "include",
                "web._assets_core",
            ),
            "web/static/src/scss/mimetypes.scss",
            "bus/static/src/*.js",
            "bus/static/src/services/**/*.js",
            "bus/static/src/workers/*.js",
            (
                "remove",
                "bus/static/src/workers/bus_worker_script.js",
            ),
            (
                "remove",
                "bus/static/src/outdated_page_watcher_service.js",
            ),
            (
                "remove",
                "bus/static/src/services/assets_watchdog_service.js",
            ),
            (
                "remove",
                "bus/static/src/simple_notification_service.js",
            ),
            (
                "include",
                "im_livechat.assets_embed_core",
            ),
            (
                "remove",
                "web/static/src/core/browser/title_service.js",
            ),
            "im_livechat/static/src/embed/external/**/*",
        ],
        "im_livechat.assets_embed_cors": [
            (
                "include",
                "im_livechat.assets_embed_external",
            ),
            "im_livechat/static/src/embed/cors/**/*",
        ],
        "im_livechat.embed_assets_unit_tests_setup": [
            (
                "include",
                "web.assets_unit_tests_setup",
            ),
            (
                "remove",
                "im_livechat/static/**",
            ),
            (
                "include",
                "im_livechat.assets_embed_external",
            ),
            (
                "remove",
                "im_livechat/static/src/embed/external/boot.js",
            ),
            (
                "remove",
                "mail/static/src/discuss/core/web/discuss_core_common_service_patch.js",
            ),
            "web/static/src/core/browser/title_service.js",
        ],
        "im_livechat.assets_livechat_support_tours": [
            "web_tour/static/src/js/**/*",
            "web/static/lib/hoot-dom/**/*",
            "web_tour/static/src/tour_utils.js",
            "web/static/tests/helpers/cleanup.js",
            "web/static/tests/helpers/utils.js",
            "web/static/tests/utils.js",
            "im_livechat/static/tests/tours/support/*",
        ],
        "im_livechat.embed_assets_unit_tests": [
            "web/static/tests/_framework/**/*",
            "web/static/tests/web_test_helpers.js",
            "bus/static/tests/bus_test_helpers.js",
            "mail/static/tests/mail_test_helpers.js",
            "mail/static/tests/mail_test_helpers_contains.js",
            "im_livechat/static/tests/livechat_test_helpers.js",
            "bus/static/tests/mock_server/**/*",
            "mail/static/tests/mock_server/**/*",
            "rating/static/tests/mock_server/**/*",
            "im_livechat/static/tests/mock_server/**/*",
            "bus/static/tests/mock_*.js",
            "im_livechat/static/tests/embed/**/*",
        ],
        "mail.assets_public": [
            "im_livechat/static/src/core/common/**/*",
            "im_livechat/static/src/core/public_web/**/*",
        ],
    },
    "esm": {
        "bundles": [
            "im_livechat.assets_embed_core",
            "im_livechat.assets_embed_cors",
            "im_livechat.assets_embed_external",
            "im_livechat.assets_livechat_support_tours",
            "im_livechat.embed_assets_unit_tests_setup",
            "im_livechat.embed_assets_unit_tests",
        ],
        "standalone_bundles": [
            "im_livechat.assets_embed_cors",
            "im_livechat.assets_embed_external",
        ],
        "import_map_includes": {
            "im_livechat.embed_assets_unit_tests_setup": [
                "im_livechat.embed_assets_unit_tests",
            ],
        },
        "dynamic_children": {
            "im_livechat.assets_embed_external": [
                "im_livechat.assets_livechat_support_tours",
            ],
        },
    },
    "application": True,
}
