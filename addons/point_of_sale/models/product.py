# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_in_pos = fields.Boolean(string='Available in Point of Sale', help='Check if you want this product to appear in the Point of Sale', default=True)
    to_weight = fields.Boolean(string='To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration")
    pos_categ_id = fields.Many2one(
        'pos.category', string='Point of Sale Category',
        help="Those categories are used to group similar products for point of sale.")

    @api.multi
    def unlink(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('available_in_pos', '=', True)]):
            if self.env['pos.session'].search_count([('state', '!=', 'closed')]):
                raise UserError(_('You cannot delete a product saleable in point of sale while a session is still opened.'))
        return super(ProductTemplate, self).unlink()


class ProductUomCateg(models.Model):
    _inherit = 'product.uom.categ'

    is_pos_groupable = fields.Boolean(string='Group Products in POS',
        help="Check if you want to group products of this category in point of sale orders")


class ProductUom(models.Model):
    _inherit = 'product.uom'

    is_pos_groupable = fields.Boolean(related='category_id.is_pos_groupable')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_pos_anglo_saxon_price_unit(self, partner_id, quantity, order_ids):
        # In the SO part, the entries will be inverted by function compute_invoice_totals
        price_unit = - self._get_anglo_saxon_price_unit()
        if self._get_invoice_policy() == "delivery":
            moves = self.env['stock.move']
            orders = self.env['pos.order'].browse(order_ids)
            pickings = orders.filtered(lambda o: o.partner_id.id == partner_id).mapped('picking_id')
            for picking in pickings:
                moves |= picking.move_lines.filtered(lambda m: m.product_id.id == self.id)
            moves.sorted(lambda x: x.date)
            average_price_unit = self._compute_average_price(quantity, quantity, moves)
            price_unit = average_price_unit or price_unit
        return price_unit
