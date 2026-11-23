# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):
    def _prepare_cart_line_data(self, line_sudo):
        line_data = super()._prepare_cart_line_data(line_sudo)
        line_data["short_summary"].extend(
            line_sudo.product_id.channel_ids.filtered(
                lambda course: course.enroll == "payment"
            ).mapped("name")
        )
        return line_data
