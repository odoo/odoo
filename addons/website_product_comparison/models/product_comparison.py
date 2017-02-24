# -*- coding: utf-8 -*-
from collections import OrderedDict

from openerp import api, fields, models


class ProductAttributeCategory(models.Model):
    _name = "product.attribute.category"
    _description = "Product Attribute Category"
    _order = 'sequence'

    name = fields.Char("Category Name", required=True)
    sequence = fields.Integer("Sequence")


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    category_id = fields.Many2one('product.attribute.category', string="Category")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_variant_groups(self):
        res = OrderedDict()
        for var in self.attribute_line_ids:
            res.setdefault(var.attribute_id.category_id.name or 'Uncategorized', []).append(var)
        return res


class ProductWishlist(models.Model):
    _name = 'product.wishlist'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist when added')
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', readonly=True)
    website_id = fields.Many2one('website', required=True)
    price = fields.Monetary(digits=0, currency_field='currency_id')
    price_new = fields.Float('Price', compute='compute_new_price')
    product_id = fields.Many2one('product.product', required=True)
    active = fields.Boolean(default=True, required=True)
    create_date = fields.Datetime('Added Date', readonly=True, required=True)

    @api.one
    @api.depends('pricelist_id', 'currency_id', 'product_id')
    def compute_new_price(self):
        self.price_new = self.product_id.with_context(pricelist=self.pricelist_id.id).website_price

    @api.model
    def _add_to_wishlist(self, partner_id, pricelist_id, currency_id, website_id, price, product_id):
        wish = self.env['product.wishlist'].create({
            'partner_id': partner_id,
            'pricelist_id': pricelist_id,
            'currency_id': currency_id,
            'website_id': website_id,
            'price': price,
            'product_id': product_id,
        })
        return wish
