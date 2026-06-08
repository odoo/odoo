# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # pos.config fields
    pos_adyen_ask_customer_for_tip = fields.Boolean(compute='_compute_pos_adyen_ask_customer_for_tip', store=True, readonly=False)

    @api.depends('pos_iface_tipproduct', 'pos_config_id')
    def _compute_pos_adyen_ask_customer_for_tip(self):
        for res_config in self:
            if res_config.pos_iface_tipproduct:
                res_config.pos_adyen_ask_customer_for_tip = res_config.pos_config_id.adyen_ask_customer_for_tip
            else:
                res_config.pos_adyen_ask_customer_for_tip = False
