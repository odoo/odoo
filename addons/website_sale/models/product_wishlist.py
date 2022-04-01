# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.http import request


class ProductWishlist(models.Model):
    _name = 'product.wishlist'
    _description = 'Product Wishlist'
    _sql_constraints = [
        ("product_unique_partner_id",
         "UNIQUE(product_id, partner_id)",
         "Duplicated wishlisted product for this partner."),
    ]

    partner_id = fields.Many2one('res.partner', string='Owner')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', help='Pricelist when added')
    price = fields.Monetary(currency_field='currency_id', string='Price',
                            help='Price of the product when it has been added in the wishlist')
    website_id = fields.Many2one('website', ondelete='cascade', required=True)
    active = fields.Boolean(default=True, required=True)
    stock_notification = fields.Boolean(default=False, required=True)
    displayed_in_cart = fields.Boolean(default=True, required=True,
                                       help='Is used to tell whether a wishlist record should be displayed in the '
                                            'user wishlist')

    @api.model
    def _add_to_wishlist(self, pricelist_id, currency_id, website_id, price, product_id, partner_id=False):
        Wishlist = self.env['product.wishlist']
        wish = Wishlist.search([('partner_id', '=', partner_id), ('product_id', '=', product_id)])
        if not wish:
            wish = Wishlist.create({
                'partner_id': partner_id,
                'product_id': product_id,
                'currency_id': currency_id,
                'pricelist_id': pricelist_id,
                'price': price,
                'website_id': website_id,
            })
        return wish

    @api.model
    def current(self):
        """Get all wishlist items that belong to current user or session,
        filter products that are unpublished."""
        if not request:
            return self

        session_wishes = self.sudo().search([('id', 'in', request.session.get('wishlist_ids', []))])
        if not self.env.user._is_public():
            website_id = self.env['website'].get_current_website().id
            partner_wishes = self.search([('partner_id', '=', self.env.user.partner_id.id), ('website_id', '=', website_id)])
            session_wishes = session_wishes | partner_wishes

        return session_wishes.filtered(lambda x: x.sudo().product_id.product_tmpl_id.website_published and x.sudo().product_id.product_tmpl_id.sale_ok)
