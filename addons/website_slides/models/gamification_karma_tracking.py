# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.addons import gamification


class GamificationKarmaTracking(gamification.GamificationKarmaTracking):

    def _get_origin_selection_values(self):
        return (
            super()._get_origin_selection_values()
            + [('slide.slide', _('Course Quiz')), ('slide.channel', self.env['ir.model']._get('slide.channel').display_name)]
        )
