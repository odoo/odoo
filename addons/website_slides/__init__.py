# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    GamificationChallenge, GamificationKarmaTracking, ResConfigSettings, ResGroups,
    ResPartner, ResUsers, SlideAnswer, SlideChannel, SlideChannelPartner, SlideChannelTag,
    SlideChannelTagGroup, SlideEmbed, SlideQuestion, SlideSlide, SlideSlidePartner,
    SlideSlideResource, SlideTag, Website,
)
from .wizard import SlideChannelInvite
