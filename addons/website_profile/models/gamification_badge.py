# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import gamification, website


class GamificationBadge(gamification.GamificationBadge, website.WebsitePublishedMixin):
