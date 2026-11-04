# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class KarmaTracking(models.Model):
    _inherit = 'gamification.karma.tracking'

    def _get_origin_selection_values(self):
        return super()._get_origin_selection_values() + [('forum.post', self.env['ir.model']._get('forum.post').display_name)]
