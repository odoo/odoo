# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team", ondelete="set null",
        help="This Point of sale's sales will be related to this Sales Team.")
    down_payment_product_id = fields.Many2one('product.product',
        string="Down Payment Product",
        help="This product will be used as down payment on a sale order.")

    def _get_special_products(self):
        res = super()._get_special_products()
        return res | self.env['pos.config'].search([]).mapped('down_payment_product_id')

    @api.model
    def _ensure_downpayment_product(self):
        pos_config = self.env.ref('point_of_sale.pos_config_main', raise_if_not_found=False)
        if pos_config:
            pos_config.write({'down_payment_product_id': self.env.ref('pos_sale.default_downpayment_product').id})

    @api.model
    def load_onboarding_furniture_scenario(self):
        super().load_onboarding_furniture_scenario()
        self._ensure_downpayment_product()
