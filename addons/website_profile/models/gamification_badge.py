# -*- coding: utf-8 -*-
from odoo.addons import website, gamification
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class GamificationBadge(models.Model, gamification.GamificationBadge, website.WebsitePublishedMixin):
