# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    partner_autocomplete_insufficient_credit = fields.Boolean('Insufficient credit', default=lambda self: self.env['iap.account'].get('partner_autocomplete').insufficient_credit)

    @api.multi
    def redirect_to_buy_autocmplete_credit(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.env['iap.account'].get_credits_url('partner_autocomplete'),
            'target': '_new',
        }
