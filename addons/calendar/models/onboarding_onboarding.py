# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Onboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_calendar_onboarding(self):
        self.action_close_panel('calendar.onboarding_onboarding_calendar')
