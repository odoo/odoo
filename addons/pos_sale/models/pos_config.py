# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_down_payment_product(self):
        return self.env.ref('pos_sale.default_downpayment_product', raise_if_not_found=False)

    def _get_default_sol_product(self):
        return self.env.ref('pos_sale.default_sol_product', raise_if_not_found=False)

    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team", ondelete="set null", index='btree_not_null',
        help="This Point of sale's sales will be related to this Sales Team.")
    down_payment_product_id = fields.Many2one('product.product',
        string="Down Payment Product",
        default=_get_default_down_payment_product,
        help="This product will be used as down payment on a sale order.")
    default_product_id = fields.Many2one(
        'product.product',
        string="Default Product",
        default=_get_default_sol_product,
        help="This product will be used as default product on productless SOLs."
    )

    def _get_special_products(self):
        res = super()._get_special_products()
        return res | self.env['pos.config'].search([]).mapped(
            lambda config: config.down_payment_product_id | config.default_product_id
        )

    @api.model
    def _ensure_default_products(self):
        values = {}

        if downpayment_product := self._get_default_down_payment_product():
            values['down_payment_product_id'] = downpayment_product.id

        if default_sol_product := self._get_default_sol_product():
            values['default_product_id'] = default_sol_product.id

        if values:
            self.with_context(active_test=False).search([]).write(values)
