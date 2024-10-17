# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.ir_http import IrHttp
from .models.ir_mail_server import IrMail_Server
from .models.ir_model import IrModel
from .models.link_tracker import LinkTracker, LinkTrackerClick
from .models.mail_blacklist import MailBlacklist
from .models.mail_mail import MailMail
from .models.mail_render_mixin import MailRenderMixin
from .models.mail_thread import MailThread
from .models.mailing import MailingMailing
from .models.mailing_contact import MailingContact
from .models.mailing_filter import MailingFilter
from .models.mailing_list import MailingList
from .models.mailing_subscription import MailingSubscription
from .models.mailing_subscription_optout import MailingSubscriptionOptout
from .models.mailing_trace import MailingTrace
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.utm_campaign import UtmCampaign
from .models.utm_medium import UtmMedium
from .models.utm_source import UtmSource
from .report.mailing_trace_report import MailingTraceReport
from .wizard.mail_compose_message import MailComposeMessage
from .wizard.mailing_contact_import import MailingContactImport
from .wizard.mailing_contact_to_list import MailingContactToList
from .wizard.mailing_list_merge import MailingListMerge
from .wizard.mailing_mailing_schedule_date import MailingMailingScheduleDate
from .wizard.mailing_mailing_test import MailingMailingTest
