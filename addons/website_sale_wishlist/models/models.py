# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductWishlist(models.Model):
    _name = 'product.wishlist'

    partner_id = fields.Many2one('res.partner', string='Customer')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist when added')
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', readonly=True)
    price_old = fields.Monetary(digits=0, currency_field='currency_id')
    website_id = fields.Many2one('website', related='pricelist_id.website_id')
    price_new = fields.Float('Price', compute='compute_new_price')
    product_id = fields.Float('product.product')

    @api.one
    @api.depends('pricelist_id', 'partner_id', 'currency_id', 'product_id')
    def compute_new_price(self):
        self.price_new = self.price_old # TODO: compute new price