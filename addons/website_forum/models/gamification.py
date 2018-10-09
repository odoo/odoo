# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Challenge(models.Model):
    _inherit = 'gamification.challenge'

    category = fields.Selection(selection_add=[('forum', 'Website / Forum')])


class Badge(models.Model):
    _inherit = 'gamification.badge'

    level = fields.Selection([('bronze', 'bronze'), ('silver', 'silver'), ('gold', 'gold')], string='Forum Badge Level')


class UserBadge(models.Model):
    _inherit = 'gamification.badge.user'

    level = fields.Selection(
        [('bronze', 'bronze'),
         ('silver', 'silver'),
         ('gold', 'gold')],
        string='Forum Badge Level',
        related="badge_id.level", store=True, readonly=False)
