# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools
from . import wizard
from . import controllers

from .models.bus_presence import BusPresence
from .models.discuss.bus_listener_mixin import BusListenerMixin
from .models.discuss.discuss_channel import DiscussChannel
from .models.discuss.discuss_channel_member import DiscussChannelMember
from .models.discuss.discuss_channel_rtc_session import DiscussChannelRtcSession
from .models.discuss.discuss_gif_favorite import DiscussGifFavorite
from .models.discuss.discuss_voice_metadata import DiscussVoiceMetadata
from .models.discuss.ir_attachment import IrAttachment
from .models.discuss.ir_binary import IrBinary
from .models.discuss.ir_websocket import IrWebsocket
from .models.discuss.mail_guest import MailGuest
from .models.discuss.mail_message import MailMessage
from .models.discuss.res_groups import ResGroups
from .models.fetchmail import FetchmailServer
from .models.ir_action_act_window import IrActionsAct_WindowView
from .models.ir_actions_server import IrActionsServer
from .models.ir_config_parameter import IrConfig_Parameter
from .models.ir_cron import IrCron
from .models.ir_http import IrHttp
from .models.ir_mail_server import IrMail_Server
from .models.ir_model import IrModel
from .models.ir_model_fields import IrModelFields
from .models.ir_qweb import IrQweb
from .models.ir_ui_menu import IrUiMenu
from .models.ir_ui_view import IrUiView
from .models.mail_activity import MailActivity
from .models.mail_activity_mixin import MailActivityMixin
from .models.mail_activity_plan import MailActivityPlan
from .models.mail_activity_plan_template import MailActivityPlanTemplate
from .models.mail_activity_type import MailActivityType
from .models.mail_alias import MailAlias
from .models.mail_alias_domain import MailAliasDomain
from .models.mail_alias_mixin import MailAliasMixin
from .models.mail_alias_mixin_optional import MailAliasMixinOptional
from .models.mail_blacklist import MailBlacklist
from .models.mail_canned_response import MailCannedResponse
from .models.mail_composer_mixin import MailComposerMixin
from .models.mail_followers import MailFollowers
from .models.mail_gateway_allowed import MailGatewayAllowed
from .models.mail_ice_server import MailIceServer
from .models.mail_link_preview import MailLinkPreview
from .models.mail_mail import MailMail
from .models.mail_message_reaction import MailMessageReaction
from .models.mail_message_schedule import MailMessageSchedule
from .models.mail_message_subtype import MailMessageSubtype
from .models.mail_message_translation import MailMessageTranslation
from .models.mail_notification import MailNotification
from .models.mail_push import MailPush
from .models.mail_push_device import MailPushDevice
from .models.mail_render_mixin import MailRenderMixin
from .models.mail_scheduled_message import MailScheduledMessage
from .models.mail_template import MailTemplate
from .models.mail_thread import MailThread
from .models.mail_thread_blacklist import MailThreadBlacklist
from .models.mail_thread_cc import MailThreadCc
from .models.mail_thread_main_attachment import MailThreadMainAttachment
from .models.mail_tracking_duration_mixin import MailTrackingDurationMixin
from .models.mail_tracking_value import MailTrackingValue
from .models.models import Base
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.res_users_settings import ResUsersSettings
from .models.res_users_settings_volumes import ResUsersSettingsVolumes
from .models.template_reset_mixin import TemplateResetMixin
from .models.update import Publisher_WarrantyContract
from .wizard.base_module_uninstall import BaseModuleUninstall
from .wizard.base_partner_merge_automatic_wizard import BasePartnerMergeAutomaticWizard
from .wizard.mail_activity_schedule import MailActivitySchedule
from .wizard.mail_blacklist_remove import MailBlacklistRemove
from .wizard.mail_compose_message import MailComposeMessage
from .wizard.mail_resend_message import MailResendMessage, MailResendPartner
from .wizard.mail_template_preview import MailTemplatePreview
from .wizard.mail_template_reset import MailTemplateReset
from .wizard.mail_wizard_invite import MailWizardInvite

def _mail_post_init(env):
    env['mail.alias.domain']._migrate_icp_to_domain()
