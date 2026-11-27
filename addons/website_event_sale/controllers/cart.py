from odoo.http import request

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):
    def _prepare_cart_line_data(self, line_sudo):
        slug = request.env["ir.http"]._slug
        line_data = super()._prepare_cart_line_data(line_sudo)

        # If the sale order line concerns an event, we want the "product" link to point to
        # the event itself and not to the product on the ecommerce
        if line_sudo.event_id:
            line_data["website_url"] = "/event/%s/register" % slug(line_sudo.event_id)

        if line_sudo.event_slot_id:
            line_data["short_summary"].append(line_sudo.event_slot_id.display_name)

        return line_data
