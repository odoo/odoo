# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.mail_group import MailGroup
from .models.mail_group_member import MailGroupMember
from .models.mail_group_message import MailGroupMessage
from .models.mail_group_moderation import MailGroupModeration
from .wizard.mail_group_message_reject import MailGroupMessageReject
