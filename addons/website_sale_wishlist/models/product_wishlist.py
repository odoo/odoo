# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
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
    price = fields.Monetary(digits=0, currency_field='currency_id', string='Price', help='Price of the product when it has been added in the wishlist')
    website_id = fields.Many2one('website', ondelete='cascade', required=True)
    active = fields.Boolean(default=True, required=True)

    @api.model
    def current(self):
        """Get all wishlist items that belong to current user or session,
        filter products that are unpublished."""
        if not request:
            return self

        if request.website.is_public_user():
            wish = self.sudo().search([('id', 'in', request.session.get('wishlist_ids', []))])
        else:
            wish = self.search([("partner_id", "=", self.env.user.partner_id.id)])

        return wish.filtered(lambda x: x.sudo().product_id.product_tmpl_id.website_published)

    @api.model
    def _add_to_wishlist(self, pricelist_id, currency_id, website_id, price, product_id, partner_id=False):
        wish = self.env['product.wishlist'].create({
            'partner_id': partner_id,
            'product_id': product_id,
            'currency_id': currency_id,
            'pricelist_id': pricelist_id,
            'price': price,
            'website_id': website_id,
        })
        return wish

    @api.model
    def _check_wishlist_from_session(self):
        """Assign all wishlist withtout partner from this the current session"""
        session_wishes = self.sudo().search([('id', 'in', request.session.get('wishlist_ids', []))])
        partner_wishes = self.sudo().search([("partner_id", "=", self.env.user.partner_id.id)])
        partner_products = partner_wishes.mapped("product_id")
        # Remove session products already present for the user
        duplicated_wishes = session_wishes.filtered(lambda wish: wish.product_id <= partner_products)
        session_wishes -= duplicated_wishes
        duplicated_wishes.unlink()
        # Assign the rest to the user
        session_wishes.write({"partner_id": self.env.user.partner_id.id})
        request.session.pop('wishlist_ids')

    @api.model
    def _garbage_collector(self, *args, **kwargs):
        """Remove wishlists for unexisting sessions."""
        self.with_context(active_test=False).search([
            ("create_date", "<", fields.Datetime.to_string(datetime.now() - timedelta(weeks=kwargs.get('wishlist_week', 5)))),
            ("partner_id", "=", False),
        ]).unlink()


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wishlist_ids = fields.One2many('product.wishlist', 'partner_id', string='Wishlist', domain=[('active', '=', True)])


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _is_in_wishlist(self):
        self.ensure_one()
        return self in self.env['product.wishlist'].current().mapped('product_id.product_tmpl_id')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _is_in_wishlist(self):
        self.ensure_one()
        return self in self.env['product.wishlist'].current().mapped('product_id')
