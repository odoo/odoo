# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    partner_autocomplete_insufficient_credit = fields.Boolean('Insufficient credit', compute="_compute_partner_autocomplete_insufficient_credit")

    def _compute_partner_autocomplete_insufficient_credit(self):
        for config in self:
            config.partner_autocomplete_insufficient_credit = self.env['iap.services']._iap_get_service_credits_balance('partner_autocomplete') <= 0

    def redirect_to_buy_autocomplete_credit(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.env['iap.services'].iap_get_service_credits_url('partner_autocomplete'),
            'target': '_new',
        }
