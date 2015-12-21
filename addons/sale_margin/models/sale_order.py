# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Float(compute='_product_margin', digits=dp.get_precision('Product Price'), store=True)
    purchase_price = fields.Float(string='Cost', digits=dp.get_precision('Product Price'))

    @api.multi
    @api.onchange('product_id', 'product_uom')
    def product_id_change_margin(self):
        for line in self:
            if line.order_id.pricelist_id:
                frm_cur = self.env.user.company_id.currency_id
                to_cur = line.order_id.pricelist_id.currency_id
                purchase_price = line.product_id.standard_price
                if line.product_uom != line.product_id.uom_id:
                    purchase_price = self.env['product.uom']._compute_price(line.product_id.uom_id.id, purchase_price, to_uom_id=line.product_uom.id)
                ctx = self.env.context.copy()
                ctx['date'] = line.order_id.date_order
                price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
                line.purchase_price = price

    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit')
    def _product_margin(self):
        for line in self:
            currency = line.order_id.pricelist_id.currency_id
            line.margin = currency.round(line.price_subtotal - ((line.purchase_price or line.product_id.standard_price) * line.product_uom_qty))


class SaleOrder(models.Model):
    _inherit = "sale.order"

    margin = fields.Monetary(compute='_product_margin', help="It gives profitability by calculating the difference between the Unit Price and the cost.", currency_field='currency_id', digits=dp.get_precision('Product Price'), store=True)

    @api.depends('order_line.margin')
    def _product_margin(self):
        for order in self:
            order.margin = sum(order.order_line.filtered(lambda r: r.state != 'cancel').mapped('margin'))
