# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_in_pos = fields.Boolean(string='Available in POS', help='Check if you want this product to appear in the Point of Sale.', default=False)
    to_weight = fields.Boolean(string='To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration.")
    pos_categ_id = fields.Many2one(
        'pos.category', string='Point of Sale Category',
        help="Category used in the Point of Sale.")

    def unlink(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('available_in_pos', '=', True)]):
            if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
                raise UserError(_('You cannot delete a product saleable in point of sale while a session is still opened.'))
        return super(ProductTemplate, self).unlink()

    @api.onchange('sale_ok')
    def _onchange_sale_ok(self):
        if not self.sale_ok:
            self.available_in_pos = False


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def unlink(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
            if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('product_tmpl_id.available_in_pos', '=', True)]):
                raise UserError(_('You cannot delete a product saleable in point of sale while a session is still opened.'))
        return super(ProductProduct, self).unlink()


class UomCateg(models.Model):
    _inherit = 'uom.category'

    is_pos_groupable = fields.Boolean(string='Group Products in POS',
        help="Check if you want to group products of this category in point of sale orders")


class Uom(models.Model):
    _inherit = 'uom.uom'

    is_pos_groupable = fields.Boolean(related='category_id.is_pos_groupable', readonly=False)
