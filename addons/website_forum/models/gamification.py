# -*- coding: utf-8 -*-

from openerp import models, fields, api


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
        related="badge_id.level", store=True)
