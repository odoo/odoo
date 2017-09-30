# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models


class ProductWishlist(models.Model):
    _name = 'product.wishlist'
    _sql_constrains = [
        ("session_or_partner_id",
         "CHECK(session IS NULL != partner_id IS NULL)",
         "Need a session or partner, but never both."),
        ("product_unique_session",
         "UNIQUE(product_id, session)",
         "Duplicated wishlisted product for this session."),
        ("product_unique_partner_id",
         "UNIQUE(product_id, partner_id)",
         "Duplicated wishlisted product for this partner."),
    ]

    partner_id = fields.Many2one('res.partner', string='Owner')
    session = fields.Char(help="Website session identifier where this product was wishlisted.")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', help='Pricelist when added')
    price = fields.Monetary(digits=0, currency_field='currency_id', string='Price', help='Price of the product when it has been added in the wishlist')
    price_new = fields.Float(compute='compute_new_price', string='Current price', help='Current price of this product, using same pricelist, ...')
    website_id = fields.Many2one('website', required=True)
    create_date = fields.Datetime('Added Date', readonly=True, required=True)
    active = fields.Boolean(default=True, required=True)

    @api.multi
    @api.depends('pricelist_id', 'currency_id', 'product_id')
    def compute_new_price(self):
        for wish in self:
            wish.price_new = wish.product_id.with_context(pricelist=wish.pricelist_id.id).website_price

    @api.model
    def current(self):
        """Get all wishlist items that belong to current user or session."""
        return self.search([
            "|",
            ("partner_id", "=", self.env.user.partner_id.id),
            "&",
            ("partner_id", "=", False),
            ("session", "=", self.env.user.current_session),
        ])

    @api.model
    def _add_to_wishlist(self, pricelist_id, currency_id, website_id, price, product_id, partner_id=False, session=False):
        wish = self.env['product.wishlist'].create({
            'partner_id': partner_id,
            'session': session,
            'product_id': product_id,
            'currency_id': currency_id,
            'pricelist_id': pricelist_id,
            'price': price,
            'website_id': website_id,
        })
        return wish

    @api.model
    def _join_current_user_and_session(self):
        """Assign all dangling session wishlisted products to user."""
        session_wishes = self.search([
            ("session", "=", self.env.user.current_session),
            ("partner_id", "=", False),
        ])
        partner_wishes = self.search([
            ("partner_id", "=", self.env.user.partner_id.id),
        ])
        partner_products = partner_wishes.mapped("product_id")
        # Remove session products already present for the user
        duplicated_wishes = session_wishes.filtered(lambda wish: wish.product_id <= partner_products)
        session_wishes -= duplicated_wishes
        duplicated_wishes.unlink()
        # Assign the rest to the user
        session_wishes.write({
            "partner_id": self.env.user.partner_id.id,
            "session": False,
        })

    @api.model
    def _garbage_collector(self, *args, **kwargs):
        """Remove wishlists for unexisting sessions."""
        self.search([
            ("create_date", "<", fields.Datetime.to_string(datetime.now() - timedelta(weeks=kwargs.get('wishlist_week', 5)))),
            ("partner_id", "=", False),
        ]).unlink()


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wishlist_ids = fields.One2many('product.wishlist', 'partner_id', string='Wishlist', domain=[('active', '=', True)])
