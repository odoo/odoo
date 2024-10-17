# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.mailing_contact import MailingContact
from .models.mailing_list import MailingList
from .models.mailing_mailing import MailingMailing
from .models.mailing_trace import MailingTrace
from .models.res_users import ResUsers
from .models.sms_sms import SmsSms
from .models.sms_tracker import SmsTracker
from .models.utm import UtmCampaign, UtmMedium
from .wizard.mailing_sms_test import MailingSmsTest
from .wizard.sms_composer import SmsComposer
