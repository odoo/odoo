# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    MailingContact, MailingList, MailingMailing, MailingTrace, ResUsers, SmsSms,
    SmsTracker, UtmCampaign, UtmMedium,
)
from .wizard import MailingSmsTest, SmsComposer
