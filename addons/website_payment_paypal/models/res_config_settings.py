# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    paypal_email_account = fields.Char()

    @api.model
    def get_values(self):
        res = super().get_values()
        paypal = self.env.ref('payment.payment_provider_paypal').sudo()
        res['paypal_email_account'] = paypal.paypal_email_account
        return res

    def set_values(self):
        super().set_values()
        paypal = self.env.ref('payment.payment_provider_paypal').sudo()
        if paypal.paypal_email_account != self.paypal_email_account:
            paypal.paypal_email_account = self.paypal_email_account
