# Part of Odoo. See LICENSE file for full copyright and licensing details.

# core models (required for mixins)
from .mail_alias import MailAlias
from .mail_alias_domain import MailAliasDomain
from .models import Base

# mixin
from .bus_listener_mixin import BusListenerMixin
from .mail_activity_mixin import MailActivityMixin
from .mail_alias_mixin_optional import MailAliasMixinOptional
from .mail_alias_mixin import MailAliasMixin
from .mail_render_mixin import MailRenderMixin
from .mail_composer_mixin import MailComposerMixin
from .mail_thread import MailThread
from .mail_thread_blacklist import MailThreadBlacklist
from .mail_thread_cc import MailThreadCc
from .mail_thread_main_attachment import MailThreadMainAttachment
from .mail_tracking_duration_mixin import MailTrackingDurationMixin
from .template_reset_mixin import TemplateResetMixin

# mail models
from .fetchmail import FetchmailServer
from .mail_notification import MailNotification  # keep before as decorated m2m
from .mail_activity_type import MailActivityType
from .mail_activity import MailActivity
from .mail_activity_plan import MailActivityPlan
from .mail_activity_plan_template import MailActivityPlanTemplate
from .mail_blacklist import MailBlacklist
from .mail_followers import MailFollowers
from .mail_gateway_allowed import MailGatewayAllowed
from .mail_link_preview import MailLinkPreview
from .mail_message_reaction import MailMessageReaction
from .mail_message_schedule import MailMessageSchedule
from .mail_message_subtype import MailMessageSubtype
from .mail_message_translation import MailMessageTranslation
from .mail_message import MailMessage
from .mail_mail import MailMail
from .mail_push import MailPush
from .mail_push_device import MailPushDevice
from .mail_scheduled_message import MailScheduledMessage
from .mail_tracking_value import MailTrackingValue
from .mail_template import MailTemplate

# discuss
from .mail_ice_server import MailIceServer
from .mail_canned_response import MailCannedResponse
from .res_users_settings import ResUsersSettings
from .res_users_settings_volumes import ResUsersSettingsVolumes

# odoo models
from .bus_presence import BusPresence
from .ir_action_act_window import IrActionsAct_WindowView
from .ir_actions_server import IrActionsServer
from .ir_attachment import IrAttachment
from .ir_config_parameter import IrConfig_Parameter
from .ir_cron import IrCron
from .ir_http import IrHttp
from .ir_mail_server import IrMail_Server
from .ir_model import IrModel
from .ir_model_fields import IrModelFields
from .ir_ui_menu import IrUiMenu
from .ir_ui_view import IrUiView
from .ir_qweb import IrQweb
from .res_company import ResCompany
from .res_config_settings import ResConfigSettings
from .res_users import ResUsers
from .update import Publisher_WarrantyContract

# after mail specifically as discuss module depends on mail
from .discuss import (
    DiscussChannel, DiscussChannelMember, DiscussChannelRtcSession,
    DiscussGifFavorite, DiscussVoiceMetadata, IrBinary, IrWebsocket, MailGuest, ResGroups,
)

# discuss_channel_member must be loaded first
from .res_partner import ResPartner
