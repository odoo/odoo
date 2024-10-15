# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .ir_http import IrHttp
from .ir_mail_server import IrMail_Server
from .ir_model import IrModel
from .link_tracker import LinkTracker, LinkTrackerClick
from .mail_blacklist import MailBlacklist
from .mailing_subscription import MailingSubscription  # keep before due to decorated m2m
from .mailing_contact import MailingContact
from .mailing_list import MailingList
from .mailing_subscription_optout import MailingSubscriptionOptout
from .mailing_trace import MailingTrace
from .mailing import MailingMailing
from .mailing_filter import MailingFilter
from .mail_mail import MailMail
from .mail_render_mixin import MailRenderMixin
from .mail_thread import MailThread
from .res_company import ResCompany
from .res_config_settings import ResConfigSettings
from .res_partner import ResPartner
from .res_users import ResUsers
from .utm_campaign import UtmCampaign
from .utm_medium import UtmMedium
from .utm_source import UtmSource
