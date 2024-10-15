# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    IapAccount, IrActionsServer, IrModel, MailFollowers, MailMessage,
    MailNotification, MailThread, ResPartner, SmsSms, SmsTemplate, SmsTracker,
)
from .wizard import (
    SmsAccountCode, SmsAccountPhone, SmsAccountSender, SmsComposer, SmsResend,
    SmsResendRecipient, SmsTemplatePreview, SmsTemplateReset,
)
