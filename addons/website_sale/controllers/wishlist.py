# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest

from odoo.http import Controller, request, route
from odoo.http.session import touch
from odoo.tools.mail import email_re


class ProductWishlist(Controller):
    @route("/shop/wishlist/add", type="jsonrpc", auth="public", website=True)
    def add_to_wishlist(self, product_id, **_kw):
        product = self.env["product.product"].browse(product_id)

        price = product._get_combination_info_variant()["price"]

        Wishlist = self.env["product.wishlist"]
        if self.env.website.is_public_user():
            Wishlist = Wishlist.sudo()
            partner_id = False
        else:
            partner_id = self.env.user.partner_id.id

        wish = Wishlist._add_to_wishlist(
            request.pricelist.id,
            self.env.website.currency_id.id,
            self.env.website.id,
            price,
            product_id,
            partner_id,
        )

        if not partner_id:
            request.session["wishlist_ids"] = request.session.get("wishlist_ids", []) + [wish.id]

        return wish

    @route("/shop/wishlist", type="http", auth="public", website=True, readonly=True, sitemap=False)
    def shop_wishlist(self, **_kw):
        wishes = self.env["product.wishlist"].current()

        return request.render(
            "website_sale.product_wishlist",
            {"wishes": wishes.with_context(display_default_code=False)},
        )

    @route("/shop/wishlist/remove/<int:wish_id>", type="jsonrpc", auth="public", website=True)
    def remove_from_wishlist(self, wish_id, **_kw):
        wish = self.env["product.wishlist"].browse(wish_id)
        if self.env.website.is_public_user():
            wish_ids = request.session.get("wishlist_ids") or []
            if wish_id in wish_ids:
                request.session["wishlist_ids"].remove(wish_id)
                touch(request.session)
                wish.sudo().unlink()
        else:
            wish.unlink()
        return True

    @route(
        "/shop/wishlist/get_product_ids", type="jsonrpc", auth="public", website=True, readonly=True
    )
    def shop_wishlist_get_product_ids(self):
        return self.env["product.wishlist"].current().product_id.ids

    @route("/shop/add/stock_notification", type="jsonrpc", auth="public", website=True)
    def add_stock_email_notification(self, email, product_id):
        # TDE FIXME: seems a bit open
        if not email_re.match(email):
            raise BadRequest(self.env._("Invalid Email"))

        product = self.env["product.product"].browse(int(product_id))
        partner = self.env["mail.thread"].sudo()._partner_find_from_emails_single([email])

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

        if self.env.website.is_public_user():
            request.session["product_with_stock_notification_enabled"] = list(
                set(request.session.get("product_with_stock_notification_enabled", []))
                | {product_id}
            )
            request.session["stock_notification_email"] = email
