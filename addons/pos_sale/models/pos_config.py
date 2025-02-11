# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv.expression import OR


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

    def _get_available_product_domain(self):
        domain = super()._get_available_product_domain()
        return OR([domain, [('id', '=', self.down_payment_product_id.id)]])
