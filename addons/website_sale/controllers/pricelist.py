# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_decode, url_encode, url_parse

from odoo.http import request, route

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website_sale.const import SHOP_PATH
from odoo.addons.website_sale.models.website import PRICELIST_SELECTED_SESSION_CACHE_KEY


class Pricelist(payment_portal.PaymentPortal):
    def _apply_pricelist(self, pricelist=None):
        """Change the pricelist of the request and recomputes the current cart prices.

        :param 'product.pricelist'|None pricelist: The new pricelist. If None resets the pricelist.
        """
        self.env.website.sudo().pricelist_id = pricelist

        if not (order_sudo := request.cart):
            return

        if pricelist:
            request.session[PRICELIST_SELECTED_SESSION_CACHE_KEY] = pricelist.id
            order_sudo.pricelist_id = pricelist
            order_sudo._recompute_prices()
        else:
            # Reset the pricelist
            request.session.pop(PRICELIST_SELECTED_SESSION_CACHE_KEY, None)
            pl_before = order_sudo.pricelist_id
            order_sudo._compute_pricelist_id()
            if order_sudo.pricelist_id != pl_before:
                order_sudo._recompute_prices()

    def _apply_selectable_pricelist(self, pricelist_id):
        """Change the pricelist if selectable on the website.

        A pricelist is applied if:
        - it is available on the current website
        - it is selectable or on the current partner

        :param int pricelist_id: the pricelist ID
        :return: True or False if the pricelist was applied or not
        :rtype: bool
        """
        if (
            self.env.website.is_pricelist_available(pricelist_id)
            and (pricelist := self.env["product.pricelist"].browse(pricelist_id))
            and (
                pricelist.selectable
                or pricelist == self.env.user.partner_id.specific_property_product_pricelist
            )
        ):
            self._apply_pricelist(pricelist=pricelist)
            return True
        return False

    @route(
        "/shop/change_pricelist/<int:pricelist_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def pricelist_change(self, pricelist_id, **_post):
        website = self.env.website
        redirect_url = request.httprequest.referrer
        prev_currency = website.currency_id
        if (
            pricelist_id
            and self._apply_selectable_pricelist(pricelist_id)
            and redirect_url
            and prev_currency != website.currency_id
            and website.is_view_active("website_sale.filter_products_price")
        ):
            # Convert prices to the new currency in the query params of the referrer
            decoded_url = url_parse(redirect_url)
            args = url_decode(decoded_url.query)
            min_price = args.get("min_price")
            max_price = args.get("max_price")
            if min_price or max_price:
                try:
                    min_price = float(min_price)
                    args["min_price"] = min_price and str(
                        prev_currency._convert(
                            min_price, website.currency_id, website.company_id, round=False
                        )
                    )
                except (ValueError, TypeError):
                    pass
                try:
                    max_price = float(max_price)
                    args["max_price"] = max_price and str(
                        prev_currency._convert(
                            max_price, website.currency_id, website.company_id, round=False
                        )
                    )
                except (ValueError, TypeError):
                    pass
            redirect_url = decoded_url.replace(query=url_encode(args)).to_url()

        return request.redirect(redirect_url or SHOP_PATH)

    @route("/shop/pricelist", type="http", auth="public", website=True, sitemap=False)
    def pricelist(self, promo, **post):
        redirect = post.get("r", "/shop/cart")
        if promo:
            pricelist_sudo = (
                self.env["product.pricelist"].sudo().search([("code", "=", promo)], limit=1)
            )
            if not (pricelist_sudo and self.env.website.is_pricelist_available(pricelist_sudo.id)):
                return request.redirect("%s?code_not_available=1" % redirect)

            self._apply_pricelist(pricelist=pricelist_sudo)
        else:
            # Reset the pricelist if empty promo code is given
            self._apply_pricelist(pricelist=None)

        return request.redirect(redirect)
