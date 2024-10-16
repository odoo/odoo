# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import gamification


class GamificationKarmaTracking(gamification.GamificationKarmaTracking):

    def _get_origin_selection_values(self):
        return super()._get_origin_selection_values() + [('forum.post', self.env['ir.model']._get('forum.post').display_name)]
