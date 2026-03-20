# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_down_payment_product(self):
        return self.env.ref('pos_sale.default_downpayment_product', raise_if_not_found=False)

    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team", ondelete="set null", index='btree_not_null',
        help="This Point of sale's sales will be related to this Sales Team.")
    down_payment_product_id = fields.Many2one('product.product',
        string="Down Payment Product",
        default=_get_default_down_payment_product,
        help="This product will be used as down payment on a sale order.")

    def _get_special_products(self):
        res = super()._get_special_products()
        return res | self.env['pos.config'].search([]).mapped('down_payment_product_id')

    @api.model
    def _ensure_downpayment_product(self):
        if downpayment_product := self._get_default_down_payment_product():
            pos_configs = self.with_context(active_test=False).search([])
            pos_configs.write({'down_payment_product_id': downpayment_product.id})
