# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Float(compute='_product_margin', digits=dp.get_precision('Product Price'), store=True)
    purchase_price = fields.Float(string='Cost', digits=dp.get_precision('Product Price'))

    def _compute_margin(self, order_id, product_id, product_uom_id):
        frm_cur = self.env.user.company_id.currency_id
        to_cur = order_id.pricelist_id.currency_id
        purchase_price = product_id.standard_price
        if product_uom_id != product_id.uom_id:
            purchase_price = product_id.uom_id._compute_price(purchase_price, product_uom_id)
        ctx = self.env.context.copy()
        ctx['date'] = order_id.date_order
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return price

    @api.model
    def _get_purchase_price(self, pricelist, product, product_uom, date):
        frm_cur = self.env.user.company_id.currency_id
        to_cur = pricelist.currency_id
        purchase_price = product.standard_price
        if product_uom != product.uom_id:
            purchase_price = product.uom_id._compute_price(purchase_price, product_uom)
        ctx = self.env.context.copy()
        ctx['date'] = date
        price = frm_cur.with_context(ctx).compute(purchase_price, to_cur, round=False)
        return {'purchase_price': price}

    @api.onchange('product_id', 'product_uom')
    def product_id_change_margin(self):
        if not self.order_id.pricelist_id or not self.product_id or not self.product_uom:
            return
        self.purchase_price = self._compute_margin(self.order_id, self.product_id, self.product_uom)

    @api.model
    def create(self, vals):
        vals.update(self._prepare_add_missing_fields(vals))

        # Calculation of the margin for programmatic creation of a SO line. It is therefore not
        # necessary to call product_id_change_margin manually
        if 'purchase_price' not in vals:
            order_id = self.env['sale.order'].browse(vals['order_id'])
            product_id = self.env['product.product'].browse(vals['product_id'])
            product_uom_id = self.env['product.uom'].browse(vals['product_uom'])

            vals['purchase_price'] = self._compute_margin(order_id, product_id, product_uom_id)

        return super(SaleOrderLine, self).create(vals)

    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'price_subtotal')
    def _product_margin(self):
        if not self.env.in_onchange:
            # prefetch the fields needed for the computation
            self.read(['price_subtotal', 'purchase_price', 'product_uom_qty', 'order_id'])
        for line in self:
            currency = line.order_id.pricelist_id.currency_id
            price = line.purchase_price
            line.margin = currency.round(line.price_subtotal - (price * line.product_uom_qty))


class SaleOrder(models.Model):
    _inherit = "sale.order"

    margin = fields.Monetary(compute='_product_margin', help="It gives profitability by calculating the difference between the Unit Price and the cost.", currency_field='currency_id', digits=dp.get_precision('Product Price'), store=True)

    @api.depends('order_line.margin')
    def _product_margin(self):
        if self.env.in_onchange:
            for order in self:
                order.margin = sum(order.order_line.filtered(lambda r: r.state != 'cancel').mapped('margin'))
        else:
            # On batch records recomputation (e.g. at install), compute the margins
            # with a single read_group query for better performance.
            # This isn't done in an onchange environment because (part of) the data
            # may not be stored in database (new records or unsaved modifications).
            grouped_order_lines_data = self.env['sale.order.line'].read_group(
                [
                    ('order_id', 'in', self.ids),
                    ('state', '!=', 'cancel'),
                ], ['margin', 'order_id'], ['order_id'])
            for data in grouped_order_lines_data:
                order = self.browse(data['order_id'][0])
                order.margin = data['margin']
