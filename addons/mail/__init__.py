# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    Base, BusListenerMixin, BusPresence, DiscussChannel, DiscussChannelMember,
    DiscussChannelRtcSession, DiscussGifFavorite, DiscussVoiceMetadata, FetchmailServer,
    IrActionsAct_WindowView, IrActionsServer, IrAttachment, IrBinary, IrConfig_Parameter, IrCron,
    IrHttp, IrMail_Server, IrModel, IrModelFields, IrQweb, IrUiMenu, IrUiView, IrWebsocket,
    MailActivity, MailActivityMixin, MailActivityPlan, MailActivityPlanTemplate, MailActivityType,
    MailAlias, MailAliasDomain, MailAliasMixin, MailAliasMixinOptional, MailBlacklist,
    MailCannedResponse, MailComposerMixin, MailFollowers, MailGatewayAllowed, MailGuest,
    MailIceServer, MailLinkPreview, MailMail, MailMessage, MailMessageReaction,
    MailMessageSchedule, MailMessageSubtype, MailMessageTranslation, MailNotification, MailPush,
    MailPushDevice, MailRenderMixin, MailScheduledMessage, MailTemplate, MailThread,
    MailThreadBlacklist, MailThreadCc, MailThreadMainAttachment, MailTrackingDurationMixin,
    MailTrackingValue, Publisher_WarrantyContract, ResCompany, ResConfigSettings, ResGroups,
    ResPartner, ResUsers, ResUsersSettings, ResUsersSettingsVolumes, TemplateResetMixin,
)
from . import tools
from .wizard import (
    BaseModuleUninstall, BasePartnerMergeAutomaticWizard, MailActivitySchedule,
    MailBlacklistRemove, MailComposeMessage, MailResendMessage, MailResendPartner,
    MailTemplatePreview, MailTemplateReset, MailWizardInvite,
)
from . import controllers

def _mail_post_init(env):
    env['mail.alias.domain']._migrate_icp_to_domain()
