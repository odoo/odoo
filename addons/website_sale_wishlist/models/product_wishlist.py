# -*- coding: utf-8 -*-
from werkzeug.exceptions import RuntimeError
from odoo import api, fields, models
from odoo.http import request


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
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', help='Pricelist when added')
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', readonly=True)
    website_id = fields.Many2one('website', required=True)
    price = fields.Monetary(digits=0, currency_field='currency_id', string='Price', help='Price of the product when it has been added in the wishlist')
    price_new = fields.Float(compute='compute_new_price', string='Current price', help='Current price of this product, using same pricelist, ...')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    session = fields.Char(help="Website session identifier where this product was wishlisted.")
    active = fields.Boolean(default=True, required=True)
    create_date = fields.Datetime('Added Date', readonly=True, required=True)


    @api.multi
    @api.depends('pricelist_id', 'currency_id', 'product_id')
    def compute_new_price(self):
        for wish in self:
            wish.price_new = wish.product_id.with_context(pricelist=wish.pricelist_id.id).website_price

    @api.model
    def current(self):
        domain = []
        try:
            domain + ["|", ("session", "=", request.session.sid)]
        except RuntimeError:
            pass  # Unbound session
        domain += [("partner_id", "=", self.env.user.partner_id.id)]
        return self.search(domain)

    @api.model
    def _add_to_wishlist(self, pricelist_id, currency_id, website_id, price, product_id, partner_id=False, session=False):
        wish = self.env['product.wishlist'].create({
            'partner_id': partner_id,
            'pricelist_id': pricelist_id,
            'currency_id': currency_id,
            'website_id': website_id,
            'price': price,
            'product_id': product_id,
            'session': session,
        })
        return wish

    @api.model
    def _join_current_user_and_session(self):
        """Assign all dangling session wishlisted products to user."""
        try:
            session_domain = [
                ("session", "=", request.session.sid),
                ("partner_id", "=", False),
            ]
        except RuntimeError:
            return  # No session is bound, nothing to join
        user_products = self.search([
            ("partner_id", "=", self.env.user.partner_id.id),
        ]).mapped("product_id")
        # Remove session products already present for the user
        self.search(session_domain + [("product_id", "in", user_products.ids)]).unlink()
        # Assign the rest to the user
        self.search(session_domain).write({
            "partner_id": self.env.user.partner_id.id,
            "session": False,
        })



class ResPartner(models.Model):
    _inherit = 'res.partner'

    wishlist_ids = fields.One2many('product.wishlist', 'partner_id', string='Wishlist', domain=[('active', '=', True)])
