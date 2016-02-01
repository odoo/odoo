# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discounted_price = fields.Float(compute='_compute_discounted_price', digits_compute=dp.get_precision('Product Price'))

    def _compute_discounted_price(self):
        for line in self:
            line.discounted_price = (line.price_unit * (1.0 - (line.discount or 0.0) / 100.0))
