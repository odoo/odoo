# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class GamificationBadge(models.Model):
    _inherit = ['gamification.badge', 'website.published.mixin']
