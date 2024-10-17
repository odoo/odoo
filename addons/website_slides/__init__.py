# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.gamification_challenge import GamificationChallenge
from .models.gamification_karma_tracking import GamificationKarmaTracking
from .models.res_config_settings import ResConfigSettings
from .models.res_groups import ResGroups
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.slide_channel import SlideChannel, SlideChannelPartner
from .models.slide_channel_tag import SlideChannelTag, SlideChannelTagGroup
from .models.slide_embed import SlideEmbed
from .models.slide_question import SlideAnswer, SlideQuestion
from .models.slide_slide import SlideSlide, SlideSlidePartner, SlideTag
from .models.slide_slide_resource import SlideSlideResource
from .models.website import Website
from .wizard.slide_channel_invite import SlideChannelInvite
