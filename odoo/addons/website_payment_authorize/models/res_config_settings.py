# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    authorize_capture_method = fields.Selection(
        string='Authorize.net: Payment Capture Method',
        selection=[
            ('auto', 'Automatically Capture Payment'),
            ('manual', 'Manually Charge Later'),
        ])

    @api.model
    def get_values(self):
        res = super().get_values()
        authorize = self.env.ref('payment.payment_provider_authorize').sudo()
        res['authorize_capture_method'] = 'manual' if authorize.capture_manually else 'auto'
        return res

    def set_values(self):
        super().set_values()
        authorize = self.env.ref('payment.payment_provider_authorize').sudo()
        capture_manually = self.authorize_capture_method == 'manual'
        if authorize.capture_manually != capture_manually:
            authorize.capture_manually = capture_manually
