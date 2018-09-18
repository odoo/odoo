# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.multi
    def action_buy_reveal_iap_credits(self):
        url = self.env['iap.account'].get_credits_url('reveal', 'https://iap.odoo.com/iap/1/credit', 0)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
