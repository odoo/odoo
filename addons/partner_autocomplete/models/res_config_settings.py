# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    partner_autocomplete_insufficient_credit = fields.Boolean('Insufficient credit', default=lambda self: self.env['iap.account'].get('partner_autocomplete').insufficient_credit)

    @api.multi
    def redirect_to_buy_autocomplete_credit(self):
        Account = self.env['iap.account']
        Account.get('partner_autocomplete').sudo().write({'insufficient_credit': False})
        return {
            'type': 'ir.actions.act_url',
            'url': Account.get_credits_url('partner_autocomplete'),
            'target': '_new',
        }
