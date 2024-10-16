# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    IrHttp, IrMail_Server, IrModel, LinkTracker, LinkTrackerClick, MailBlacklist,
    MailMail, MailRenderMixin, MailThread, MailingContact, MailingFilter, MailingList,
    MailingMailing, MailingSubscription, MailingSubscriptionOptout, MailingTrace, ResCompany,
    ResConfigSettings, ResPartner, ResUsers, UtmCampaign, UtmMedium, UtmSource,
)
from .report import MailingTraceReport
from .wizard import (
    MailComposeMessage, MailingContactImport, MailingContactToList,
    MailingListMerge, MailingMailingScheduleDate, MailingMailingTest,
)
