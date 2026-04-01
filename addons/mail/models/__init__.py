# Part of Odoo. See LICENSE file for full copyright and licensing details.

# core models (required for mixins)
from . import mail_alias
from . import mail_alias_domain
from . import models

# mixin
from . import mail_activity_mixin
from . import mail_alias_mixin_optional
from . import mail_alias_mixin
from . import mail_render_mixin
from . import mail_composer_mixin
from . import mail_thread
from . import mail_thread_blacklist
from . import mail_thread_cc
from . import mail_thread_main_attachment
from . import mail_tracking_duration_mixin
from . import template_reset_mixin

# mail models
from . import fetchmail
from . import mail_notification  # keep before as decorated m2m
from . import mail_activity_type
from . import mail_activity
from . import mail_activity_plan
from . import mail_activity_plan_template
from . import mail_blacklist
from . import mail_followers
from . import mail_gateway_allowed
from . import mail_link_preview
from . import mail_message_link_preview
from . import mail_message_reaction
from . import mail_message_schedule
from . import mail_message_subtype
from . import mail_message_translation
from . import mail_message
from . import mail_mail
from . import mail_presence
from . import mail_push
from . import mail_push_device
from . import mail_scheduled_message
from . import mail_tracking_value
from . import mail_template

# discuss
from . import mail_ice_server
from . import mail_canned_response
from . import res_users_settings
from . import res_users_settings_volumes

# odoo models
from . import ir_action_act_window
from . import ir_actions_server
from . import ir_attachment
from . import ir_config_parameter
from . import ir_cron
from . import ir_http
from . import ir_mail_server
from . import ir_model
from . import ir_model_fields
from . import ir_ui_menu
from . import ir_ui_view
from . import ir_qweb
from . import ir_websocket
from . import res_company
from . import res_config_settings
from . import res_role
from . import res_users
from . import update

# after mail specifically as discuss module depends on mail
from . import discuss

# discuss_channel_member must be loaded first
from . import res_partner
