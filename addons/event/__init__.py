# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    EventEvent, EventEventTicket, EventMail, EventMailRegistration, EventQuestion,
    EventQuestionAnswer, EventRegistration, EventRegistrationAnswer, EventStage, EventTag,
    EventTagCategory, EventType, EventTypeMail, EventTypeTicket, MailTemplate, ResConfigSettings,
    ResPartner,
)
from . import report
from . import tools
