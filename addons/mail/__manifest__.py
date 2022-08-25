# -*- coding: utf-8 -*-

{
    'name': 'Discuss',
    'version': '1.10',
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
    'depends': ['base', 'base_setup', 'bus', 'web_tour'],
    'data': [
        'data/mail_groups.xml',
        'wizard/mail_blacklist_remove_views.xml',
        'wizard/mail_compose_message_views.xml',
        'wizard/mail_resend_message_views.xml',
        'wizard/mail_template_preview_views.xml',
        'wizard/mail_wizard_invite_views.xml',
        'wizard/mail_template_reset_views.xml',
        'views/fetchmail_views.xml',
        'views/mail_message_subtype_views.xml',
        'views/mail_tracking_views.xml',
        'views/mail_notification_views.xml',
        'views/mail_message_views.xml',
        'views/mail_message_schedule_views.xml',
        'views/mail_mail_views.xml',
        'views/mail_followers_views.xml',
        'views/mail_ice_server_views.xml',
        'views/mail_channel_member_views.xml',
        'views/mail_channel_rtc_session_views.xml',
        'views/mail_channel_views.xml',
        'views/mail_shortcode_views.xml',
        'views/mail_activity_views.xml',
        'views/res_config_settings_views.xml',
        'data/res_partner_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_templates_chatter.xml',
        'data/mail_templates_email_layouts.xml',
        'data/mail_templates_mailgateway.xml',
        'data/mail_channel_data.xml',
        'data/mail_activity_data.xml',
        'data/ir_cron_data.xml',
        'security/mail_security.xml',
        'security/ir.model.access.csv',
        'views/discuss_public_templates.xml',
        'views/mail_alias_views.xml',
        'views/mail_gateway_allowed_views.xml',
        'views/mail_guest_views.xml',
        'views/mail_message_reaction_views.xml',
        'views/res_users_views.xml',
        'views/res_users_settings_views.xml',
        'views/mail_template_views.xml',
        'views/ir_actions_server_views.xml',
        'views/ir_model_views.xml',
        'views/res_partner_views.xml',
        'views/mail_blacklist_views.xml',
        'views/mail_menus.xml',
    ],
    'demo': [
        'data/mail_channel_demo.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'mail.assets_messaging': [
            'mail/static/src/model/*.js',
            'mail/static/src/models/*.js',
        ],
        # Custom bundle in case we want to remove things that are later added to web.assets_common
        'mail.assets_common_discuss_public': [
            ('include', 'web.assets_common'),
        ],
        'mail.assets_discuss_public': [
            # SCSS dependencies (the order is important)
            ('include', 'web._assets_helpers'),
            'web/static/src/legacy/scss/bootstrap_overridden.scss',
            'web/static/src/libs/bootstrap/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/src/legacy/scss/import_bootstrap.scss',
            'web/static/src/libs/bootstrap/utilities_custom.scss',
            'web/static/lib/bootstrap/scss/utilities/_api.scss',
            'web/static/src/legacy/scss/bootstrap_review.scss',
            'web/static/src/webclient/webclient.scss',
            'web/static/src/webclient/webclient_extra.scss',
            'web/static/src/core/utils/*.scss',
            # depends on BS variables, can't be loaded in assets_primary or assets_secondary
            'mail/static/src/scss/variables/derived_variables.scss',
            'mail/static/src/scss/composer.scss',
            # Dependency of notification_group, notification_request, thread_needaction_preview and thread_preview
            'mail/static/src/components/notification_list/notification_list_item.scss',
            'mail/static/src/component_hooks/*.js',
            'mail/static/src/components/*/*',
            # Unused by guests and depends on ViewDialogs, better to remove it instead of pulling the whole view dependency tree
            ('remove', 'mail/static/src/components/composer_suggested_recipient/*'),
            ('remove', 'mail/static/src/components/activity_menu_container/*'),
            'mail/static/src/js/emojis.js',
            'mail/static/src/js/utils.js',
            ('include', 'mail.assets_messaging'),
            'mail/static/src/public/*',
            'mail/static/src/services/*.js',
            ('remove', 'mail/static/src/services/systray_service.js'),
            'mail/static/src/utils/*.js',
            # Framework JS
            'web/static/lib/luxon/luxon.js',
            'web/static/src/core/**/*',
            # FIXME: debug menu currently depends on webclient, once it doesn't we don't need to remove the contents of the debug folder
            ('remove', 'web/static/src/core/debug/**/*'),
            'web/static/src/env.js',
            'web/static/src/legacy/js/core/misc.js',
            'web/static/src/legacy/js/env.js',
            'web/static/src/legacy/js/fields/field_utils.js',
            'web/static/src/legacy/js/owl_compatibility.js',
            'web/static/src/legacy/js/services/data_manager.js',
            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/widgets/date_picker.js',
            'web/static/src/legacy/legacy_load_views.js',
            'web/static/src/legacy/legacy_promise_error_handler.js',
            'web/static/src/legacy/legacy_rpc_error_handler.js',
            'web/static/src/legacy/utils.js',
            'web/static/src/legacy/xml/base.xml',
        ],
        'web.assets_frontend': [
            'mail/static/src/utils/*.js',
            'mail/static/src/js/emojis.js',
            'mail/static/src/js/utils.js',
            'mail/static/src/component_hooks/*.js',
             ('include', 'mail.assets_messaging'),
            'mail/static/src/services/messaging_service.js',
        ],
        'web._assets_primary_variables': [
            'mail/static/src/scss/variables/primary_variables.scss',
        ],
        'web.assets_backend': [
            # depends on BS variables, can't be loaded in assets_primary or assets_secondary
            'mail/static/src/scss/variables/derived_variables.scss',
            # defines mixins and variables used by multiple components
            'mail/static/src/components/notification_list/notification_list_item.scss',
            'mail/static/src/js/**/*.js',
            'mail/static/src/utils/*.js',
            'mail/static/src/scss/*.scss',
            'mail/static/src/component_hooks/*.js',
            'mail/static/src/components/*/*.js',
            'mail/static/src/components/*/*.scss',
            ('include', 'mail.assets_messaging'),
            'mail/static/src/services/*.js',
            'mail/static/src/views/**/*.js',
            'mail/static/src/webclient/commands/*.js',
            'mail/static/src/widgets/*/*.js',
            'mail/static/src/widgets/*/*.scss',
        ],
        'web.assets_backend_prod_only': [
            'mail/static/src/main.js',
        ],
        'mail.assets_discuss_public_test_tours': [
            'mail/static/tests/tours/discuss_public_tour.js',
            'mail/static/tests/tours/mail_channel_as_guest_tour.js',
        ],
        'web.assets_tests': [
            'mail/static/tests/tours/**/*',
        ],
        'web.tests_assets': [
            'mail/static/tests/helpers/*.js',
            'mail/static/tests/models/*.js',
        ],
        'web.qunit_suite_tests': [
            'mail/static/tests/qunit_suite_tests/**/*.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'mail/static/tests/qunit_mobile_suite_tests/**/*.js',
        ],
        'web.assets_qweb': [
            'mail/static/src/xml/*.xml',
            'mail/static/src/components/*/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
