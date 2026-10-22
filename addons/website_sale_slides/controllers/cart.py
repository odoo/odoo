# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):
    def _prepare_cart_summary_line_data(self, line):
        line_data = super()._prepare_cart_summary_line_data(line)
        line_data["courses"] = (
            (
                course.name
                for course in line.product_id.channel_ids.filtered(
                    lambda course: course.enroll == "payment"
                )
            )
            if line.product_id.channel_ids
            else []
        )
        return line_data
