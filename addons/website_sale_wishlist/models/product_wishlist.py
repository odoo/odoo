# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models
from odoo.http import request


class ProductWishlist(models.Model):
    _inherit = 'product.wishlist'

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

    @api.autovacuum
    def _gc_sessions(self, *args, **kwargs):
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

    def _is_in_wishlist(self):
        self.ensure_one()
        return self in self.env['product.wishlist'].current().mapped('product_id.product_tmpl_id')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_in_wishlist(self):
        self.ensure_one()
        return self in self.env['product.wishlist'].current().filtered(lambda wish: wish.displayed_in_cart).mapped('product_id')
