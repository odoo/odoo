# -*- coding: utf-8 -*-

from openerp import models, fields, api


class gamification_challenge(models.Model):
    _inherit = 'gamification.challenge'

    @api.model
    def _get_categories(self):
        res = super(gamification_challenge, self)._get_categories()
        res.append(('forum', 'Website / Forum'))
        return res


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
