# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.iap_account import IapAccount
from .models.ir_actions_server import IrActionsServer
from .models.ir_model import IrModel
from .models.mail_followers import MailFollowers
from .models.mail_message import MailMessage
from .models.mail_notification import MailNotification
from .models.mail_thread import MailThread
from .models.res_partner import ResPartner
from .models.sms_sms import SmsSms
from .models.sms_template import SmsTemplate
from .models.sms_tracker import SmsTracker
from .wizard.sms_account_code import SmsAccountCode
from .wizard.sms_account_phone import SmsAccountPhone
from .wizard.sms_account_sender import SmsAccountSender
from .wizard.sms_composer import SmsComposer
from .wizard.sms_resend import SmsResend, SmsResendRecipient
from .wizard.sms_template_preview import SmsTemplatePreview
from .wizard.sms_template_reset import SmsTemplateReset
