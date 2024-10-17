# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import tools

from .models.event_event import EventEvent, EventType
from .models.event_mail import EventMail, EventTypeMail
from .models.event_mail_registration import EventMailRegistration
from .models.event_question import EventQuestion
from .models.event_question_answer import EventQuestionAnswer
from .models.event_registration import EventRegistration
from .models.event_registration_answer import EventRegistrationAnswer
from .models.event_stage import EventStage
from .models.event_tag import EventTag, EventTagCategory
from .models.event_ticket import EventEventTicket, EventTypeTicket
from .models.mail_template import MailTemplate
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
