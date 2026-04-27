# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random


from odoo import api, fields, models


class HrTimesheetTip(models.Model):
    _name = "hr.timesheet.tip"
    _description = "Timesheets Leaderboard Tip"

    name = fields.Char('Tip Name', required=True, translate=True)

    @api.model
    def _get_random_tip(self):
        all_tips = self.search([])
        if not all_tips:
            return False
        return random.choice(all_tips).name
