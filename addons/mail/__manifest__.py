# -*- coding: utf-8 -*-

{
    'name': 'Discuss',
    'version': '1.2',
    'category': 'Productivity/Discuss',
    'sequence': 145,
    'summary': 'Chat, mail gateway and private channels',
    'description': "",
    'website': 'https://www.odoo.com/page/discuss',
    'depends': ['base', 'base_setup', 'bus', 'web_tour'],
    'data': [
        'wizard/invite_view.xml',
        'wizard/mail_blacklist_remove_view.xml',
        'wizard/mail_compose_message_view.xml',
        'wizard/mail_resend_cancel_views.xml',
        'wizard/mail_resend_message_views.xml',
        'wizard/mail_template_preview_views.xml',
        'views/mail_message_subtype_views.xml',
        'views/mail_tracking_views.xml',
        'views/mail_notification_views.xml',
        'views/mail_message_views.xml',
        'views/mail_mail_views.xml',
        'views/mail_followers_views.xml',
        'views/mail_moderation_views.xml',
        'views/mail_channel_partner_views.xml',
        'views/mail_channel_views.xml',
        'views/mail_shortcode_views.xml',
        'views/mail_activity_views.xml',
        'views/res_config_settings_views.xml',
        'data/ir_config_parameter_data.xml',
        'data/res_partner_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_templates.xml',
        'data/mail_channel_data.xml',
        'data/mail_activity_data.xml',
        'data/ir_cron_data.xml',
        'security/mail_security.xml',
        'security/ir.model.access.csv',
        'views/mail_alias_views.xml',
        'views/res_users_views.xml',
        'views/mail_template_views.xml',
        'views/ir_actions_views.xml',
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
        'web._assets_primary_variables': [
            # after //link[last()]
            'mail/static/src/scss/variables.scss',
        ],
        'web.assets_backend': [
            # inside .
            'mail/static/src/js/core/translation.js',
            # inside .
            'mail/static/src/js/many2many_tags_email.js',
            # inside .
            'mail/static/src/js/many2one_avatar_user.js',
            # inside .
            'mail/static/src/js/field_char.js',
            # inside .
            'mail/static/src/js/document_viewer.js',
            # inside .
            'mail/static/src/js/basic_view.js',
            # inside .
            'mail/static/src/js/systray/systray_activity_menu.js',
            # inside .
            'mail/static/src/js/tours/mail.js',
            # inside .
            'mail/static/src/js/tools/debug_manager.js',
            # inside .
            'mail/static/src/js/custom_filter_item.js',
            # inside .
            'mail/static/src/js/utils.js',
            # inside .
            'mail/static/src/js/activity.js',
            # inside .
            'mail/static/src/js/views/activity/activity_view.js',
            # inside .
            'mail/static/src/js/views/activity/activity_model.js',
            # inside .
            'mail/static/src/js/views/activity/activity_controller.js',
            # inside .
            'mail/static/src/js/views/activity/activity_renderer.js',
            # inside .
            'mail/static/src/js/views/activity/activity_record.js',
            # inside .
            'mail/static/src/js/views/activity/activity_cell.js',
            # inside .
            'mail/static/src/js/emojis.js',
            # inside .
            'mail/static/src/js/emojis_mixin.js',
            # inside .
            'mail/static/src/js/field_emojis_common.js',
            # inside .
            'mail/static/src/js/field_char_emojis.js',
            # inside .
            'mail/static/src/js/field_text_emojis.js',
            # inside .
            'mail/static/src/scss/emojis.scss',
            # inside .
            'mail/static/src/variables.scss',
            # inside .
            'mail/static/src/scss/discuss.scss',
            # inside .
            'mail/static/src/scss/composer.scss',
            # inside .
            'mail/static/src/scss/thread.scss',
            # inside .
            'mail/static/src/scss/systray.scss',
            # inside .
            'mail/static/src/scss/mail_activity.scss',
            # inside .
            'mail/static/src/scss/many2one_avatar_user.scss',
            # inside .
            'mail/static/src/scss/activity_view.scss',
            # inside .
            'mail/static/src/scss/kanban_view.scss',
            # inside .
            'mail/static/src/bugfix/bugfix.js',
            # inside .
            'mail/static/src/component_hooks/use_drag_visible_dropzone/use_drag_visible_dropzone.js',
            # inside .
            'mail/static/src/component_hooks/use_refs/use_refs.js',
            # inside .
            'mail/static/src/component_hooks/use_rendered_values/use_rendered_values.js',
            # inside .
            'mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js',
            # inside .
            'mail/static/src/component_hooks/use_store/use_store.js',
            # inside .
            'mail/static/src/component_hooks/use_update/use_update.js',
            # inside .
            'mail/static/src/components/activity/activity.js',
            # inside .
            'mail/static/src/components/activity_box/activity_box.js',
            # inside .
            'mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover.js',
            # inside .
            'mail/static/src/components/attachment/attachment.js',
            # inside .
            'mail/static/src/components/attachment_box/attachment_box.js',
            # inside .
            'mail/static/src/components/attachment_delete_confirm_dialog/attachment_delete_confirm_dialog.js',
            # inside .
            'mail/static/src/components/attachment_list/attachment_list.js',
            # inside .
            'mail/static/src/components/attachment_viewer/attachment_viewer.js',
            # inside .
            'mail/static/src/components/autocomplete_input/autocomplete_input.js',
            # inside .
            'mail/static/src/components/chat_window/chat_window.js',
            # inside .
            'mail/static/src/components/chat_window_header/chat_window_header.js',
            # inside .
            'mail/static/src/components/chat_window_hidden_menu/chat_window_hidden_menu.js',
            # inside .
            'mail/static/src/components/chat_window_manager/chat_window_manager.js',
            # inside .
            'mail/static/src/components/chatter/chatter.js',
            # inside .
            'mail/static/src/components/chatter_container/chatter_container.js',
            # inside .
            'mail/static/src/components/chatter_topbar/chatter_topbar.js',
            # inside .
            'mail/static/src/components/composer/composer.js',
            # inside .
            'mail/static/src/components/composer_suggested_recipient/composer_suggested_recipient.js',
            # inside .
            'mail/static/src/components/composer_suggested_recipient_list/composer_suggested_recipient_list.js',
            # inside .
            'mail/static/src/components/composer_suggestion/composer_suggestion.js',
            # inside .
            'mail/static/src/components/composer_suggestion_list/composer_suggestion_list.js',
            # inside .
            'mail/static/src/components/composer_text_input/composer_text_input.js',
            # inside .
            'mail/static/src/components/dialog/dialog.js',
            # inside .
            'mail/static/src/components/dialog_manager/dialog_manager.js',
            # inside .
            'mail/static/src/components/discuss/discuss.js',
            # inside .
            'mail/static/src/components/discuss_mobile_mailbox_selection/discuss_mobile_mailbox_selection.js',
            # inside .
            'mail/static/src/components/discuss_sidebar/discuss_sidebar.js',
            # inside .
            'mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js',
            # inside .
            'mail/static/src/components/drop_zone/drop_zone.js',
            # inside .
            'mail/static/src/components/editable_text/editable_text.js',
            # inside .
            'mail/static/src/components/emojis_popover/emojis_popover.js',
            # inside .
            'mail/static/src/components/file_uploader/file_uploader.js',
            # inside .
            'mail/static/src/components/follow_button/follow_button.js',
            # inside .
            'mail/static/src/components/follower/follower.js',
            # inside .
            'mail/static/src/components/follower_list_menu/follower_list_menu.js',
            # inside .
            'mail/static/src/components/follower_subtype/follower_subtype.js',
            # inside .
            'mail/static/src/components/follower_subtype_list/follower_subtype_list.js',
            # inside .
            'mail/static/src/components/mail_template/mail_template.js',
            # inside .
            'mail/static/src/components/message/message.js',
            # inside .
            'mail/static/src/components/message_author_prefix/message_author_prefix.js',
            # inside .
            'mail/static/src/components/message_list/message_list.js',
            # inside .
            'mail/static/src/components/message_seen_indicator/message_seen_indicator.js',
            # inside .
            'mail/static/src/components/messaging_menu/messaging_menu.js',
            # inside .
            'mail/static/src/components/mobile_messaging_navbar/mobile_messaging_navbar.js',
            # inside .
            'mail/static/src/components/moderation_ban_dialog/moderation_ban_dialog.js',
            # inside .
            'mail/static/src/components/moderation_discard_dialog/moderation_discard_dialog.js',
            # inside .
            'mail/static/src/components/moderation_reject_dialog/moderation_reject_dialog.js',
            # inside .
            'mail/static/src/components/notification_alert/notification_alert.js',
            # inside .
            'mail/static/src/components/notification_group/notification_group.js',
            # inside .
            'mail/static/src/components/notification_list/notification_list.js',
            # inside .
            'mail/static/src/components/notification_popover/notification_popover.js',
            # inside .
            'mail/static/src/components/notification_request/notification_request.js',
            # inside .
            'mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js',
            # inside .
            'mail/static/src/components/thread_icon/thread_icon.js',
            # inside .
            'mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js',
            # inside .
            'mail/static/src/components/thread_preview/thread_preview.js',
            # inside .
            'mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js',
            # inside .
            'mail/static/src/components/thread_typing_icon/thread_typing_icon.js',
            # inside .
            'mail/static/src/components/thread_view/thread_view.js',
            # inside .
            'mail/static/src/model/model_core.js',
            # inside .
            'mail/static/src/model/model_errors.js',
            # inside .
            'mail/static/src/model/model_field.js',
            # inside .
            'mail/static/src/model/model_field_command.js',
            # inside .
            'mail/static/src/model/model_manager.js',
            # inside .
            'mail/static/src/models/activity/activity.js',
            # inside .
            'mail/static/src/models/activity_type/activity_type.js',
            # inside .
            'mail/static/src/models/attachment/attachment.js',
            # inside .
            'mail/static/src/models/attachment_viewer/attachment_viewer.js',
            # inside .
            'mail/static/src/models/canned_response/canned_response.js',
            # inside .
            'mail/static/src/models/channel_command/channel_command.js',
            # inside .
            'mail/static/src/models/chat_window/chat_window.js',
            # inside .
            'mail/static/src/models/chat_window_manager/chat_window_manager.js',
            # inside .
            'mail/static/src/models/chatter/chatter.js',
            # inside .
            'mail/static/src/models/composer/composer.js',
            # inside .
            'mail/static/src/models/country/country.js',
            # inside .
            'mail/static/src/models/device/device.js',
            # inside .
            'mail/static/src/models/dialog/dialog.js',
            # inside .
            'mail/static/src/models/dialog_manager/dialog_manager.js',
            # inside .
            'mail/static/src/models/discuss/discuss.js',
            # inside .
            'mail/static/src/models/follower/follower.js',
            # inside .
            'mail/static/src/models/follower_subtype/follower_subtype.js',
            # inside .
            'mail/static/src/models/follower_subtype_list/follower_subtype_list.js',
            # inside .
            'mail/static/src/models/locale/locale.js',
            # inside .
            'mail/static/src/models/mail_template/mail_template.js',
            # inside .
            'mail/static/src/models/message/message.js',
            # inside .
            'mail/static/src/models/message_seen_indicator/message_seen_indicator.js',
            # inside .
            'mail/static/src/models/messaging/messaging.js',
            # inside .
            'mail/static/src/models/messaging_initializer/messaging_initializer.js',
            # inside .
            'mail/static/src/models/messaging_menu/messaging_menu.js',
            # inside .
            'mail/static/src/models/messaging_notification_handler/messaging_notification_handler.js',
            # inside .
            'mail/static/src/models/model/model.js',
            # inside .
            'mail/static/src/models/notification/notification.js',
            # inside .
            'mail/static/src/models/notification_group/notification_group.js',
            # inside .
            'mail/static/src/models/notification_group_manager/notification_group_manager.js',
            # inside .
            'mail/static/src/models/partner/partner.js',
            # inside .
            'mail/static/src/models/suggested_recipient_info/suggested_recipient_info.js',
            # inside .
            'mail/static/src/models/thread/thread.js',
            # inside .
            'mail/static/src/models/thread_cache/thread_cache.js',
            # inside .
            'mail/static/src/models/thread_partner_seen_info/thread_partner_seen_info.js',
            # inside .
            'mail/static/src/models/thread_view/thread_view.js',
            # inside .
            'mail/static/src/models/thread_view/thread_viewer.js',
            # inside .
            'mail/static/src/models/user/user.js',
            # inside .
            'mail/static/src/services/chat_window_service/chat_window_service.js',
            # inside .
            'mail/static/src/services/dialog_service/dialog_service.js',
            # inside .
            'mail/static/src/services/messaging/messaging.js',
            # inside .
            'mail/static/src/utils/deferred/deferred.js',
            # inside .
            'mail/static/src/utils/throttle/throttle.js',
            # inside .
            'mail/static/src/utils/timer/timer.js',
            # inside .
            'mail/static/src/utils/utils.js',
            # inside .
            'mail/static/src/widgets/discuss/discuss.js',
            # inside .
            'mail/static/src/widgets/discuss_invite_partner_dialog/discuss_invite_partner_dialog.js',
            # inside .
            'mail/static/src/widgets/form_renderer/form_renderer.js',
            # inside .
            'mail/static/src/widgets/messaging_menu/messaging_menu.js',
            # inside .
            'mail/static/src/widgets/notification_alert/notification_alert.js',
            # inside .
            'mail/static/src/components/notification_list/notification_list_item.scss',
            # inside .
            'mail/static/src/bugfix/bugfix.scss',
            # inside .
            'mail/static/src/components/activity/activity.scss',
            # inside .
            'mail/static/src/components/activity_box/activity_box.scss',
            # inside .
            'mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover.scss',
            # inside .
            'mail/static/src/components/attachment/attachment.scss',
            # inside .
            'mail/static/src/components/attachment_box/attachment_box.scss',
            # inside .
            'mail/static/src/components/attachment_list/attachment_list.scss',
            # inside .
            'mail/static/src/components/attachment_viewer/attachment_viewer.scss',
            # inside .
            'mail/static/src/components/chat_window/chat_window.scss',
            # inside .
            'mail/static/src/components/chat_window_header/chat_window_header.scss',
            # inside .
            'mail/static/src/components/chat_window_hidden_menu/chat_window_hidden_menu.scss',
            # inside .
            'mail/static/src/components/chat_window_manager/chat_window_manager.scss',
            # inside .
            'mail/static/src/components/chatter/chatter.scss',
            # inside .
            'mail/static/src/components/chatter_container/chatter_container.scss',
            # inside .
            'mail/static/src/components/chatter_topbar/chatter_topbar.scss',
            # inside .
            'mail/static/src/components/composer/composer.scss',
            # inside .
            'mail/static/src/components/composer_suggested_recipient/composer_suggested_recipient.scss',
            # inside .
            'mail/static/src/components/composer_suggested_recipient_list/composer_suggested_recipient_list.scss',
            # inside .
            'mail/static/src/components/composer_suggestion/composer_suggestion.scss',
            # inside .
            'mail/static/src/components/composer_suggestion_list/composer_suggestion_list.scss',
            # inside .
            'mail/static/src/components/composer_text_input/composer_text_input.scss',
            # inside .
            'mail/static/src/components/dialog/dialog.scss',
            # inside .
            'mail/static/src/components/discuss/discuss.scss',
            # inside .
            'mail/static/src/components/discuss_mobile_mailbox_selection/discuss_mobile_mailbox_selection.scss',
            # inside .
            'mail/static/src/components/discuss_sidebar/discuss_sidebar.scss',
            # inside .
            'mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.scss',
            # inside .
            'mail/static/src/components/drop_zone/drop_zone.scss',
            # inside .
            'mail/static/src/components/emojis_popover/emojis_popover.scss',
            # inside .
            'mail/static/src/components/file_uploader/file_uploader.scss',
            # inside .
            'mail/static/src/components/follow_button/follow_button.scss',
            # inside .
            'mail/static/src/components/follower/follower.scss',
            # inside .
            'mail/static/src/components/follower_list_menu/follower_list_menu.scss',
            # inside .
            'mail/static/src/components/follower_subtype/follower_subtype.scss',
            # inside .
            'mail/static/src/components/follower_subtype_list/follower_subtype_list.scss',
            # inside .
            'mail/static/src/components/mail_template/mail_template.scss',
            # inside .
            'mail/static/src/components/message/message.scss',
            # inside .
            'mail/static/src/components/message_author_prefix/message_author_prefix.scss',
            # inside .
            'mail/static/src/components/message_list/message_list.scss',
            # inside .
            'mail/static/src/components/message_seen_indicator/message_seen_indicator.scss',
            # inside .
            'mail/static/src/components/messaging_menu/messaging_menu.scss',
            # inside .
            'mail/static/src/components/mobile_messaging_navbar/mobile_messaging_navbar.scss',
            # inside .
            'mail/static/src/components/notification_group/notification_group.scss',
            # inside .
            'mail/static/src/components/notification_list/notification_list.scss',
            # inside .
            'mail/static/src/components/notification_popover/notification_popover.scss',
            # inside .
            'mail/static/src/components/notification_request/notification_request.scss',
            # inside .
            'mail/static/src/components/partner_im_status_icon/partner_im_status_icon.scss',
            # inside .
            'mail/static/src/components/thread_icon/thread_icon.scss',
            # inside .
            'mail/static/src/components/thread_needaction_preview/thread_needaction_preview.scss',
            # inside .
            'mail/static/src/components/thread_preview/thread_preview.scss',
            # inside .
            'mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.scss',
            # inside .
            'mail/static/src/components/thread_typing_icon/thread_typing_icon.scss',
            # inside .
            'mail/static/src/components/thread_view/thread_view.scss',
            # inside .
            'mail/static/src/widgets/discuss/discuss.scss',
            # inside .
            'mail/static/src/widgets/form_renderer/form_renderer.scss',
        ],
        'web.assets_backend_prod_only': [
            # inside .
            'mail/static/src/js/main.js',
        ],
        'web.assets_tests': [
            # inside .
            'mail/static/tests/tours/mail_full_composer_test_tour.js',
        ],
        'web.tests_assets': [
            # inside .
            'mail/static/src/env/test_env.js',
            # inside .
            'mail/static/src/utils/test_utils.js',
            # inside .
            'mail/static/tests/helpers/mock_models.js',
            # inside .
            'mail/static/tests/helpers/mock_server.js',
        ],
        'web.qunit_suite_tests': [
            # inside .
            'mail/static/tests/chatter_tests.js',
            # inside .
            'mail/static/tests/mail_utils_tests.js',
            # inside .
            'mail/static/tests/document_viewer_tests.js',
            # inside .
            'mail/static/tests/many2one_avatar_user_tests.js',
            # inside .
            'mail/static/tests/systray/systray_activity_menu_tests.js',
            # inside .
            'mail/static/tests/tools/debug_manager_tests.js',
            # inside .
            'mail/static/tests/activity_tests.js',
            # inside .
            'mail/static/src/bugfix/bugfix_tests.js',
            # inside .
            'mail/static/src/component_hooks/use_store/use_store_tests.js',
            # inside .
            'mail/static/src/components/activity/activity_tests.js',
            # inside .
            'mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover_tests.js',
            # inside .
            'mail/static/src/components/attachment/attachment_tests.js',
            # inside .
            'mail/static/src/components/attachment_box/attachment_box_tests.js',
            # inside .
            'mail/static/src/components/chat_window_manager/chat_window_manager_tests.js',
            # inside .
            'mail/static/src/components/chatter/chatter_tests.js',
            # inside .
            'mail/static/src/components/chatter/chatter_suggested_recipient_tests.js',
            # inside .
            'mail/static/src/components/chatter_topbar/chatter_topbar_tests.js',
            # inside .
            'mail/static/src/components/composer/composer_tests.js',
            # inside .
            'mail/static/src/components/composer_suggestion/composer_suggestion_canned_response_tests.js',
            # inside .
            'mail/static/src/components/composer_suggestion/composer_suggestion_channel_tests.js',
            # inside .
            'mail/static/src/components/composer_suggestion/composer_suggestion_command_tests.js',
            # inside .
            'mail/static/src/components/composer_suggestion/composer_suggestion_partner_tests.js',
            # inside .
            'mail/static/src/components/dialog_manager/dialog_manager_tests.js',
            # inside .
            'mail/static/src/components/discuss/tests/discuss_domain_tests.js',
            # inside .
            'mail/static/src/components/discuss/tests/discuss_inbox_tests.js',
            # inside .
            'mail/static/src/components/discuss/tests/discuss_moderation_tests.js',
            # inside .
            'mail/static/src/components/discuss/tests/discuss_pinned_tests.js',
            # inside .
            'mail/static/src/components/discuss/tests/discuss_sidebar_tests.js',
            # inside .
            'mail/static/src/components/discuss/tests/discuss_tests.js',
            # inside .
            'mail/static/src/components/file_uploader/file_uploader_tests.js',
            # inside .
            'mail/static/src/components/follow_button/follow_button_tests.js',
            # inside .
            'mail/static/src/components/follower/follower_tests.js',
            # inside .
            'mail/static/src/components/follower_list_menu/follower_list_menu_tests.js',
            # inside .
            'mail/static/src/components/follower_subtype/follower_subtype_tests.js',
            # inside .
            'mail/static/src/components/message/message_tests.js',
            # inside .
            'mail/static/src/components/message_seen_indicator/message_seen_indicator_tests.js',
            # inside .
            'mail/static/src/components/messaging_menu/messaging_menu_tests.js',
            # inside .
            'mail/static/src/components/notification_list/notification_list_notification_group_tests.js',
            # inside .
            'mail/static/src/components/notification_list/notification_list_tests.js',
            # inside .
            'mail/static/src/components/partner_im_status_icon/partner_im_status_icon_tests.js',
            # inside .
            'mail/static/src/components/thread_icon/thread_icon_tests.js',
            # inside .
            'mail/static/src/components/thread_needaction_preview/thread_needaction_preview_tests.js',
            # inside .
            'mail/static/src/components/thread_preview/thread_preview_tests.js',
            # inside .
            'mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status_tests.js',
            # inside .
            'mail/static/src/components/thread_view/thread_view_tests.js',
            # inside .
            'mail/static/src/models/attachment/attachment_tests.js',
            # inside .
            'mail/static/src/models/message/message_tests.js',
            # inside .
            'mail/static/src/models/messaging/messaging_tests.js',
            # inside .
            'mail/static/src/models/thread/thread_tests.js',
            # inside .
            'mail/static/src/utils/throttle/throttle_tests.js',
            # inside .
            'mail/static/src/utils/timer/timer_tests.js',
            # inside .
            'mail/static/src/widgets/form_renderer/form_renderer_tests.js',
            # inside .
            'mail/static/src/widgets/notification_alert/notification_alert_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            # inside .
            'mail/static/src/components/discuss_mobile_mailbox_selection/discuss_mobile_mailbox_selection_tests.js',
        ],
        'web.assets_qweb': [
            'mail/static/src/xml/activity.xml',
            'mail/static/src/xml/activity_view.xml',
            'mail/static/src/xml/composer.xml',
            'mail/static/src/xml/many2one_avatar_user.xml',
            'mail/static/src/xml/systray.xml',
            'mail/static/src/xml/thread.xml',
            'mail/static/src/xml/web_kanban_activity.xml',
            'mail/static/src/xml/text_emojis.xml',
            'mail/static/src/bugfix/bugfix.xml',
            'mail/static/src/components/activity/activity.xml',
            'mail/static/src/components/activity_box/activity_box.xml',
            'mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover.xml',
            'mail/static/src/components/attachment/attachment.xml',
            'mail/static/src/components/attachment_box/attachment_box.xml',
            'mail/static/src/components/attachment_delete_confirm_dialog/attachment_delete_confirm_dialog.xml',
            'mail/static/src/components/attachment_list/attachment_list.xml',
            'mail/static/src/components/attachment_viewer/attachment_viewer.xml',
            'mail/static/src/components/autocomplete_input/autocomplete_input.xml',
            'mail/static/src/components/chat_window/chat_window.xml',
            'mail/static/src/components/chat_window_header/chat_window_header.xml',
            'mail/static/src/components/chat_window_hidden_menu/chat_window_hidden_menu.xml',
            'mail/static/src/components/chat_window_manager/chat_window_manager.xml',
            'mail/static/src/components/chatter/chatter.xml',
            'mail/static/src/components/chatter_container/chatter_container.xml',
            'mail/static/src/components/chatter_topbar/chatter_topbar.xml',
            'mail/static/src/components/composer/composer.xml',
            'mail/static/src/components/composer_suggested_recipient/composer_suggested_recipient.xml',
            'mail/static/src/components/composer_suggested_recipient_list/composer_suggested_recipient_list.xml',
            'mail/static/src/components/composer_suggestion/composer_suggestion.xml',
            'mail/static/src/components/composer_suggestion_list/composer_suggestion_list.xml',
            'mail/static/src/components/composer_text_input/composer_text_input.xml',
            'mail/static/src/components/dialog/dialog.xml',
            'mail/static/src/components/dialog_manager/dialog_manager.xml',
            'mail/static/src/components/discuss/discuss.xml',
            'mail/static/src/components/discuss_mobile_mailbox_selection/discuss_mobile_mailbox_selection.xml',
            'mail/static/src/components/discuss_sidebar/discuss_sidebar.xml',
            'mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.xml',
            'mail/static/src/components/drop_zone/drop_zone.xml',
            'mail/static/src/components/editable_text/editable_text.xml',
            'mail/static/src/components/emojis_popover/emojis_popover.xml',
            'mail/static/src/components/file_uploader/file_uploader.xml',
            'mail/static/src/components/follow_button/follow_button.xml',
            'mail/static/src/components/follower/follower.xml',
            'mail/static/src/components/follower_list_menu/follower_list_menu.xml',
            'mail/static/src/components/follower_subtype/follower_subtype.xml',
            'mail/static/src/components/follower_subtype_list/follower_subtype_list.xml',
            'mail/static/src/components/mail_template/mail_template.xml',
            'mail/static/src/components/message/message.xml',
            'mail/static/src/components/message_author_prefix/message_author_prefix.xml',
            'mail/static/src/components/message_list/message_list.xml',
            'mail/static/src/components/message_seen_indicator/message_seen_indicator.xml',
            'mail/static/src/components/messaging_menu/messaging_menu.xml',
            'mail/static/src/components/mobile_messaging_navbar/mobile_messaging_navbar.xml',
            'mail/static/src/components/moderation_ban_dialog/moderation_ban_dialog.xml',
            'mail/static/src/components/moderation_discard_dialog/moderation_discard_dialog.xml',
            'mail/static/src/components/moderation_reject_dialog/moderation_reject_dialog.xml',
            'mail/static/src/components/notification_alert/notification_alert.xml',
            'mail/static/src/components/notification_group/notification_group.xml',
            'mail/static/src/components/notification_list/notification_list.xml',
            'mail/static/src/components/notification_popover/notification_popover.xml',
            'mail/static/src/components/notification_request/notification_request.xml',
            'mail/static/src/components/partner_im_status_icon/partner_im_status_icon.xml',
            'mail/static/src/components/thread_icon/thread_icon.xml',
            'mail/static/src/components/thread_needaction_preview/thread_needaction_preview.xml',
            'mail/static/src/components/thread_preview/thread_preview.xml',
            'mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.xml',
            'mail/static/src/components/thread_typing_icon/thread_typing_icon.xml',
            'mail/static/src/components/thread_view/thread_view.xml',
            'mail/static/src/widgets/common.xml',
            'mail/static/src/widgets/discuss/discuss.xml',
            'mail/static/src/widgets/discuss_invite_partner_dialog/discuss_invite_partner_dialog.xml',
            'mail/static/src/widgets/messaging_menu/messaging_menu.xml',
        ],
    }
}
