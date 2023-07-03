# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import UserError


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('paytm', "PayTM")], ondelete={'paytm': 'set default'})
    paytm_mid = fields.Char(string="PayTM Merchant ID", required_if_provider='paytm')
    merchant_key = fields.Char(string="PayTM Merchant API Key", required_if_provider='paytm')

    def _get_supported_currencies(self):
        """ Override of `payment` to return INR as the only supported currency. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'paytm':
            supported_currencies = supported_currencies.filtered(lambda c: c.name == 'INR')
        return supported_currencies

    def _onchange_state_switch_is_published(self):
        if self.code == 'paytm':
            return
        super()._onchange_state_switch_is_published()

    def action_toggle_is_published(self):
        if self.code == 'paytm':
            raise UserError("PayTM payment provider can not be published.")
        super().action_toggle_is_published()
