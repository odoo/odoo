# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = "sale.order"

    margin = fields.Monetary(compute='_product_margin', help="It gives profitability by calculating the difference between the Unit Price and the cost price.",
                             currency_field='currency_id', digits=dp.get_precision('Product Price'), store=True)

    @api.one
    @api.depends('order_line.margin')
    def _product_margin(self):
        self.margin = sum(line.margin for line in self.order_line if line.state != 'cancel')
