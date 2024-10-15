# -*- coding: utf-8 -*-
from . import controllers
from .models import (
    ChatbotMessage, ChatbotScript, ChatbotScriptAnswer, ChatbotScriptStep,
    DigestDigest, DiscussChannel, DiscussChannelMember, Im_LivechatChannel,
    Im_LivechatChannelRule, IrBinary, MailMessage, RatingRating, ResPartner, ResUsers,
    ResUsersSettings,
)
from .report import Im_LivechatReportChannel, Im_LivechatReportOperator
from . import demo
from . import tools
