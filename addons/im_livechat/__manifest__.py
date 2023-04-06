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
        "report/im_livechat_report_channel_views.xml",
        "report/im_livechat_report_operator_views.xml"
    ],
    'demo': [
        "data/im_livechat_channel_demo.xml",
        'data/discuss_shortcode_demo.xml',
    ],
    'depends': ["mail", "rating", "digest", "utm"],
    'installable': True,
    'application': True,
    'assets': {
        'web._assets_primary_variables': [
            'im_livechat/static/src/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'web/static/src/core/commands/*',
            'web/static/src/core/debug/*',
            'web/static/src/views/fields/file_handler.*',
            'web/static/src/views/fields/formatters.js',
            ('include', 'im_livechat.shared_frontend_public_assets'),
            'im_livechat/static/src/new/frontend/**/*',
        ],
        'web.assets_backend': [
            'im_livechat/static/src/js/colors_reset_button/*',
            'im_livechat/static/src/js/im_livechat_chatbot_steps_one2many.js',
            'im_livechat/static/src/js/im_livechat_chatbot_script_answers_m2m.js',
            'im_livechat/static/src/chat_window/**/*',
            'im_livechat/static/src/composer/**/*',
            'im_livechat/static/src/core/**/*',
            'im_livechat/static/src/discuss_app/**/*',
            'im_livechat/static/src/messaging_menu/**/*',
            'im_livechat/static/src/web/**/*',
            'im_livechat/static/src/scss/im_livechat_history.scss',
            'im_livechat/static/src/scss/im_livechat_form.scss',
        ],
        'web.tests_assets': [
            'im_livechat/static/tests/helpers/**/*.js',
        ],
        'web.qunit_suite_tests': [
            'im_livechat/static/tests/**/*',
            ('remove', 'im_livechat/static/tests/tours/**/*'),
            ('remove', 'im_livechat/static/tests/helpers/**/*.js'),
        ],
        'web.assets_tests': [
            'im_livechat/static/tests/tours/**/*',
        ],
        'im_livechat.shared_frontend_public_assets': [
            # Those imports are required by the action service which is
            # required by the chat window expand feature which is not
            # available in public livechat.
            # TODO: split this feature to remove those deps
            'web/static/src/search/**/*',
            'web/static/src/views/view.js',
            'web/static/src/views/view_hook.js',
            'web/static/src/views/onboarding_banner.js',
            'web/static/src/webclient/actions/action_service.js',
            'web/static/src/webclient/actions/action_hook.js',
            'web/static/src/webclient/actions/action_dialog.js',
            'web/static/src/webclient/actions/reports/report_action.js',
            'web/static/src/webclient/actions/reports/report_hook.js',
            'web/static/src/views/utils.js',
            # ===== END OF ACTION SERVICE DEPS =====

            'mail/static/src/core/**/*',
            'mail/static/src/core_ui/**/*',
            'mail/static/src/utils/**/*',
            'mail/static/src/emoji_picker/**/*',
            'mail/static/src/attachments/**/*',
            'mail/static/src/composer/**/*',
            'mail/static/src/dropzone/**/*',
            'mail/static/src/rtc**/*',
            'mail/static/src/web/chat_window/**/*',
            'mail/static/src/web/discuss_app/context_service.js',
            'mail/static/src/discuss_app/**/*',
            ('remove', 'mail/static/src/**/*.dark.scss'),

            'im_livechat/static/src/new/**/*',
            'im_livechat/static/src/livechat_data.js',
            ('remove', 'im_livechat/static/src/new/frontend/**/*'),
            ('remove', 'im_livechat/static/src/new/public/**/*'),
        ],
        'im_livechat.assets_embed': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            ('include', 'web.assets_common'),
            ('include', 'web._assets_bootstrap'),
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/webclient/webclient.scss',
            'web/static/src/core/utils/transitions.scss',  # included early because used by other files
            'web/static/src/core/**/*',
            'web/static/src/env.js',
            ('remove', 'web/static/src/legacy/js/services/ajax_service.js'),
            'web/static/src/views/fields/formatters.js',
            'web/static/src/views/fields/file_handler.*',

            'web/static/src/legacy/js/core/misc.js',
            'web/static/src/legacy/js/env.js',
            'web/static/src/legacy/js/owl_compatibility.js',
            'web/static/src/legacy/js/services/data_manager.js',
            'web/static/src/legacy/legacy_load_views.js',
            'web/static/src/legacy/utils.js',
            'web/static/src/legacy/js/public/public_root.js',
            'web/static/src/legacy/js/public/lazyloader.js',
            'web/static/src/legacy/js/public/public_env.js',
            'web/static/src/legacy/js/public/public_widget.js',

            'bus/static/src/bus_parameters_service.js',

            ('include', 'im_livechat.shared_frontend_public_assets'),
            'im_livechat/static/src/new/public/**/*',
            'im_livechat/static/src/public/bus_parameters_service_patch.js',
            'im_livechat/static/src/public/session.js',
        ],
    },
    'license': 'LGPL-3',
}
