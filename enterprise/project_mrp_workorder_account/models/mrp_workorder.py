# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _update_productivity_analytic(self, old_dist):
        for time in self.time_ids:
            time._create_analytic_entry(previous_duration=0, old_dist=old_dist)
