# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controller
from . import models
from . import tools

from .models.link_tracker import LinkTracker, LinkTrackerClick, LinkTrackerCode
from .models.mail_render_mixin import MailRenderMixin
from .models.utm import UtmCampaign
