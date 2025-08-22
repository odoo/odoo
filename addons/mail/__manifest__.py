# -*- coding: utf-8 -*-

{
    'name': 'Discuss',
    'version': '1.19',
    'category': 'Productivity/Discuss',
    'sequence': 145,
    'summary': 'Chat, mail gateway and private channels',
    'description': """

Chat, mail gateway and private channel.
=======================================

Communicate with your colleagues/customers/guest within Odoo.

Discuss/Chat
------------
User-friendly "Discuss" features that allows one 2 one or group communication
(text chat/voice call/video call), invite guests and share documents with
them, all real-time.

Mail gateway
------------
Sending information and documents made simplified. You can send emails
from Odoo itself, and that too with great possibilities. For example,
design a beautiful email template for the invoices, and use the same
for all your customers, no need to do the same exercise every time.

Chatter
-------
Do all the contextual conversation on a document. For example on an
applicant, directly post an update to send email to the applicant,
schedule the next interview call, attach the contract, add HR officer
to the follower list to notify them for important events(with help of
subtypes),...


Retrieve incoming email on POP/IMAP servers.
============================================
Enter the parameters of your POP/IMAP account(s), and any incoming emails on
these accounts will be automatically downloaded into your Odoo system. All
POP3/IMAP-compatible servers are supported, included those that require an
encrypted SSL/TLS connection.
This can be used to easily create email-based workflows for many email-enabled Odoo documents, such as:
----------------------------------------------------------------------------------------------------------
    * CRM Leads/Opportunities
    * CRM Claims
    * Project Issues
    * Project Tasks
    * Human Resource Recruitment (Applicants)
Just install the relevant application, and you can assign any of these document
types (Leads, Project Issues) to your incoming email accounts. New emails will
automatically spawn new documents of the chosen type, so it's a snap to create a
mailbox-to-Odoo integration. Even better: these documents directly act as mini
conversations synchronized by email. You can reply from within Odoo, and the
answers will automatically be collected when they come back, and attached to the
same *conversation* document.
For more specific needs, you may also assign custom-defined actions
(technically: Server Actions) to be triggered for each incoming mail.
    """,
    'website': 'https://www.odoo.com/app/discuss',
    'depends': ['base', 'base_setup', 'bus', 'web_tour', 'html_editor'],
    'data': [
        'data/mail_groups.xml',
        'wizard/mail_activity_schedule_views.xml',
        'wizard/mail_blacklist_remove_views.xml',
        'wizard/mail_compose_message_views.xml',
        'wizard/mail_template_preview_views.xml',
        'wizard/mail_followers_edit_views.xml',
        'wizard/mail_template_reset_views.xml',
        'views/fetchmail_views.xml',
        'views/ir_cron_views.xml',
        'views/ir_filters_views.xml',
        'views/ir_mail_server_views.xml',
        'views/mail_message_subtype_views.xml',
        'views/mail_tracking_value_views.xml',
        'views/mail_notification_views.xml',
        'views/mail_message_views.xml',
        'views/mail_message_schedule_views.xml',
        'views/mail_mail_views.xml',
        'views/mail_followers_views.xml',
        'views/mail_ice_server_views.xml',
        'views/discuss_channel_member_views.xml',
        'views/discuss_channel_rtc_session_views.xml',
        'views/mail_link_preview_views.xml',
        'views/discuss/discuss_gif_favorite_views.xml',
        'views/discuss_channel_views.xml',
        'views/mail_canned_response_views.xml',
        'views/res_role_views.xml',
        'views/mail_activity_views.xml',
        'views/mail_activity_plan_views.xml',
        'views/mail_activity_plan_template_views.xml',
        'views/res_config_settings_views.xml',
        'data/ir_config_parameter_data.xml',
        'data/res_partner_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_templates_chatter.xml',
        'data/mail_templates_email_layouts.xml',
        'data/mail_templates_mailgateway.xml',
        'data/discuss_channel_data.xml',
        'data/mail_activity_type_data.xml',
        'data/security_notifications_templates.xml',
        'data/ir_cron_data.xml',
        'data/ir_actions_client.xml',
        'security/mail_security.xml',
        'security/ir.model.access.csv',
        'views/discuss_public_templates.xml',
        'views/mail_alias_domain_views.xml',
        'views/mail_alias_views.xml',
        'views/mail_gateway_allowed_views.xml',
        'views/mail_guest_views.xml',
        'views/mail_message_reaction_views.xml',
        'views/mail_templates_public.xml',
        'views/res_users_views.xml',
        'views/res_users_settings_views.xml',
        'views/mail_template_views.xml',
        'views/ir_actions_server_views.xml',
        'views/ir_model_views.xml',
        'views/res_partner_views.xml',
        'views/mail_blacklist_views.xml',
        'views/mail_menus.xml',
        'views/discuss/discuss_menus.xml',
        'views/discuss/discuss_call_history_views.xml',
        'views/res_company_views.xml',
        "views/mail_scheduled_message_views.xml",
        "data/mail_canned_response_data.xml",
        'data/mail_templates_invite.xml',
        'data/web_tour_tour.xml',
    ],
    'demo': [
        'demo/mail_activity_demo.xml',
        'demo/discuss_channel_demo.xml',
        'demo/discuss/public_channel_demo.xml',
        "demo/mail_canned_response_demo.xml",
    ],
    'installable': True,
    'application': True,
    'post_init_hook': '_mail_post_init',
    'assets': {
        'web._assets_primary_variables': [
            'mail/static/src/**/primary_variables.scss',
        ],
        'web.assets_backend': [
            # depends on BS variables, can't be loaded in assets_primary or assets_secondary
            'mail/static/src/scss/variables/derived_variables.scss',
            'mail/static/src/scss/*.scss',
            'mail/static/lib/selfie_segmentation/selfie_segmentation.js',
            'mail/static/src/js/**/*',
            'mail/static/src/model/**/*',
            'mail/static/src/core/common/**/*',
            'mail/static/src/core/public_web/**/*',
            'mail/static/src/core/web_portal/**/*',
            'mail/static/src/core/web/**/*',
            'mail/static/src/**/common/**/*',
            'mail/static/src/**/public_web/**/*',
            'mail/static/src/**/web_portal/**/*',
            'mail/static/src/**/web/**/*',
            ('remove', 'mail/static/src/**/*.dark.scss'),
            # discuss (loaded last to fix dependencies)
            ('remove', 'mail/static/src/discuss/**/*'),
            'mail/static/src/discuss/core/common/**/*',
            'mail/static/src/discuss/core/public_web/**/*',
            'mail/static/src/discuss/core/web/**/*',
            'mail/static/src/discuss/**/common/**/*',
            'mail/static/src/discuss/**/public_web/**/*',
            'mail/static/src/discuss/**/web/**/*',
            ('remove', 'mail/static/src/discuss/**/*.dark.scss'),
            'mail/static/src/views/fields/**/*',
            ('remove', 'mail/static/src/views/web/activity/**'),
        ],
        'web.assets_backend_lazy': [
            'mail/static/src/views/web/activity/**',
        ],
        "web.assets_web_dark": [
            'mail/static/src/**/*.dark.scss',
        ],
        "web.assets_frontend": [
            "mail/static/src/utils/common/format.js",
        ],
        'mail.assets_discuss_public_test_tours': [
            'web/static/lib/hoot-dom/**/*',
            'web_tour/static/src/js/**/*',
            'web_tour/static/src/tour_utils.js',
            'web/static/tests/legacy/helpers/cleanup.js',
            'web/static/tests/legacy/helpers/utils.js',
            'web/static/tests/legacy/utils.js',
            'mail/static/tests/tours/discuss_channel_public_tour.js',
            'mail/static/tests/tours/discuss_channel_as_guest_tour.js',
            'mail/static/tests/tours/discuss_channel_call_action.js',
            'mail/static/tests/tours/discuss_channel_call_public_tour.js',
            'mail/static/tests/tours/discuss_sidebar_in_public_page_tour.js',
            'mail/static/tests/tours/discuss_channel_meeting_view_tour.js',
        ],
        # Unit test files
        'web.assets_unit_tests': [
            'mail/static/tests/**/*',
            ('remove', 'mail/static/tests/legacy/helpers/mock_services.js'), # to remove when all legacy tests are ported
            ('remove', 'mail/static/tests/tours/**/*'),
        ],
        'web.assets_tests': [
            'mail/static/tests/tours/**/*',
        ],
        'web.tests_assets': [
            'mail/static/tests/legacy/helpers/mock_services.js',
        ],
        'mail.assets_odoo_sfu': [
            'mail/static/lib/odoo_sfu/odoo_sfu.js',
        ],
        'mail.assets_lamejs': [
            'mail/static/lib/lame/lame.js',
        ],
        'mail.assets_public': [
            'web/static/lib/jquery/jquery.js',
            'web/static/lib/odoo_ui_icons/style.css',
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            ('include', 'web._assets_bootstrap_backend'),
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/animation.scss',
            'web/static/src/webclient/webclient.scss',
            'web/static/src/scss/mimetypes.scss',
            'web/static/src/scss/ui.scss',
            ('include', 'web._assets_core'),
            'web/static/src/views/fields/formatters.js',
            'web/static/src/views/fields/file_handler.*',

            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            'bus/static/src/workers/*.js',
            ('remove', 'bus/static/src/workers/bus_worker_script.js'),

            ("include", "html_editor.assets_editor"),

            'mail/static/src/model/**/*',
            'mail/static/src/core/common/**/*',
            'mail/static/src/core/public_web/**/*',
            'mail/static/src/**/common/**/*',
            'mail/static/src/**/public_web/**/*',
            'mail/static/src/**/public/**/*',
            'mail/static/lib/selfie_segmentation/selfie_segmentation.js',
            ('remove', 'mail/static/src/**/*.dark.scss'),
            # discuss (loaded last to fix dependencies)
            ('remove', 'mail/static/src/discuss/**/*'),
            'mail/static/src/discuss/core/common/**/*',
            'mail/static/src/discuss/core/public_web/**/*',
            'mail/static/src/discuss/core/public/**/*',
            'mail/static/src/discuss/**/common/**/*',
            'mail/static/src/discuss/**/public_web/**/*',
            'mail/static/src/discuss/**/public/**/*',
            ('remove', 'mail/static/src/discuss/**/*.dark.scss'),
            ('remove', 'web/static/src/**/*.dark.scss'),
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
