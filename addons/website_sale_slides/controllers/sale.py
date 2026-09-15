from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_sale.controllers.main import WebsiteSale

_debug = DebugLog(__name__)


class WebsiteSaleSlides(WebsiteSale):
    def _prepare_shop_payment_confirmation_values(self, order):
        values = super()._prepare_shop_payment_confirmation_values(order)
        if order.line_ids.product_id.channel_ids:
            channel_partners = (
                request.env["slide.channel.partner"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", order.partner_id.id),
                        ("channel_id", "in", order.line_ids.product_id.channel_ids.ids),
                    ]
                )
            )
            values["course_memberships"] = {
                channel_partner.channel_id: channel_partner
                for channel_partner in channel_partners
            }
            _debug.pipeline(
                "course_memberships_on_confirmation",
                order=order,
                channels=order.line_ids.product_id.channel_ids,
                memberships=channel_partners,
            )
        return values
