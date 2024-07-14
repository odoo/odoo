# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Onboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    # Appointment Onboarding
    @api.model
    def action_close_panel_appointment(self):
        self.action_close_panel('appointment.onboarding_onboarding_appointment')
