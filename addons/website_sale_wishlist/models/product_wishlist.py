from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductWishlist(models.Model):
    _name = "product.wishlist"
    _description = "Product Wishlist"
    _product_unique_partner_id = models.UniqueIndex(
        "(product_id, partner_id) WHERE partner_id IS NOT NULL",
        "Duplicated wishlisted product for this partner.",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Owner",
        index="btree_not_null",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="website_id.currency_id",
        readonly=True,
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        help="Pricelist when added",
    )
    price = fields.Monetary(
        currency_field="currency_id",
        help="Price of the product when it has been added in the wishlist",
    )
    website_id = fields.Many2one(
        comodel_name="website",
        required=True,
        ondelete="cascade",
    )
    active = fields.Boolean(
        default=True,
        required=True,
    )

    @api.model
    def current(self):
        if not request:
            return self

        if request.env.user._is_public():
            wish = self.sudo().search(
                [("id", "in", request.session.get("wishlist_ids", []))]
            )
        else:
            wish = self.search(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("website_id", "=", request.website.id),
                ]
            )

        _debug.pipeline(
            "wishlist_candidates",
            candidates=wish,
            anonymous=request.env.user._is_public(),
        )
        return wish.filtered(
            lambda wish: (
                wish.sudo().product_id.product_tmpl_id.website_published
                and wish.sudo().product_id.product_tmpl_id._is_add_to_cart_possible()
            )
        )

    @api.model
    def _add_to_wishlist(
        self, pricelist_id, currency_id, website_id, price, product_id, partner_id=False
    ):
        return self.env["product.wishlist"].create(
            {
                "partner_id": partner_id,
                "product_id": product_id,
                "currency_id": currency_id,
                "pricelist_id": pricelist_id,
                "price": price,
                "website_id": website_id,
            }
        )

    @api.model
    def _check_wishlist_from_session(self):
        session_wishes = self.sudo().search(
            [("id", "in", request.session.get("wishlist_ids", []))]
        )
        partner_wishes = self.sudo().search(
            [("partner_id", "=", self.env.user.partner_id.id)]
        )
        partner_products = partner_wishes.mapped("product_id")
        duplicated_wishes = session_wishes.filtered(
            lambda wish: wish.product_id <= partner_products
        )
        session_wishes -= duplicated_wishes
        _debug.lifecycle(
            "wishlist_session_merged",
            partner=self.env.user.partner_id,
            adopted=session_wishes,
            dropped_as_duplicate=duplicated_wishes,
            already_owned=len(partner_wishes),
        )
        duplicated_wishes.unlink()
        session_wishes.write({"partner_id": self.env.user.partner_id.id})
        request.session.pop("wishlist_ids")

    @api.autovacuum
    def _gc_sessions(self, *args, **kwargs):
        with _debug.perf(
            "wishlist_gc", cr=self.env.cr, weeks=kwargs.get("wishlist_week", 5)
        ):
            self.with_context(active_test=False).search(
                [
                    (
                        "create_date",
                        "<",
                        fields.Datetime.to_string(
                            datetime.now()
                            - timedelta(weeks=kwargs.get("wishlist_week", 5))
                        ),
                    ),
                    ("partner_id", "=", False),
                ]
            ).unlink()


class ResPartner(models.Model):
    _inherit = "res.partner"

    wishlist_ids = fields.One2many(
        comodel_name="product.wishlist",
        inverse_name="partner_id",
        domain=[("active", "=", True)],
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _is_in_wishlist(self):
        self.check_singleton()
        return self in self.env["product.wishlist"].current().mapped(
            "product_id.product_tmpl_id"
        )


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _is_in_wishlist(self):
        self.check_singleton()
        return self in self.env["product.wishlist"].current().mapped("product_id")
