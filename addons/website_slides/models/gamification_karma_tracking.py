from odoo import models


class GamificationKarmaTracking(models.Model):
    _inherit = "gamification.karma.tracking"

    def _selection_origin_models(self):
        return super()._selection_origin_models() + [
            ("slide.slide", self.env._("Course Quiz")),
            ("slide.channel", self.env["ir.model"]._get("slide.channel").display_name),
        ]
