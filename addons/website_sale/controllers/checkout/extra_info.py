# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment.controllers import portal as payment_portal

_lt = LazyTranslate(__name__)


class ExtraInfo(payment_portal.PaymentPortal):
    def system_page_extra_info(env):  # noqa: N805
        if env.website.is_view_active("website_sale.extra_info"):
            return _lt("Shop Checkout - Extra Information")
        return False

    @route(
        ["/shop/extra_info"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=system_page_extra_info,
    )
    def extra_info(self, **post):
        order_sudo = request.cart
        extra_step = self.env.website.viewref("website_sale.extra_info")
        if not extra_step.active or not self.env.website._cart_has_extra_step_category():
            return request.redirect(
                self.env.website._get_next_breadcrumb_step_href("/shop/extra_info")
            )

        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/extra_info", order_sudo
        ):
            return request.redirect(redirect)

        values = {
            "website_sale_order": order_sudo,
            "post": post,
            "escape": lambda x: x.replace("'", r"\'"),
            "partner": order_sudo.partner_id.id,
            "order": order_sudo,
        }

        values.update(self.env.website._get_checkout_step_values("/shop/extra_info"))

        return request.render("website_sale.extra_info", values)
