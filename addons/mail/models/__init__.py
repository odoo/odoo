# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# core models (required for mixins)
from . import mail_alias
from . import models

# mixin
from . import mail_activity_mixin
from . import mail_alias_mixin
from . import mail_render_mixin
from . import mail_composer_mixin
from . import mail_thread
from . import mail_thread_blacklist
from . import mail_thread_cc
from . import template_reset_mixin

# mail models
from . import fetchmail
from . import mail_notification  # keep before as decorated m2m
from . import mail_activity_type
from . import mail_activity
from . import mail_blacklist
from . import mail_followers
from . import mail_gateway_allowed
from . import mail_message_reaction
from . import mail_message_schedule
from . import mail_message_subtype
from . import mail_message
from . import mail_mail
from . import mail_tracking_value
from . import mail_template

# discuss
from . import mail_channel_member
from . import mail_channel_rtc_session
from . import mail_channel
from . import mail_guest
from . import mail_ice_server
from . import mail_shortcode
from . import res_users_settings
from . import res_users_settings_volumes

# odoo models
from . import bus_presence
from . import ir_action_act_window
from . import ir_actions_server
from . import ir_attachment
from . import ir_config_parameter
from . import ir_http
from . import ir_model
from . import ir_model_fields
from . import ir_translation
from . import ir_ui_view
from . import ir_qweb
from . import ir_websocket
from . import res_company
from . import res_config_settings
from . import res_partner
from . import res_users
from . import res_groups
from . import update
