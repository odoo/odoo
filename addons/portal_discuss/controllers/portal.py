# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class DiscussCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "discuss_count" in counters:
            values["discuss_count"] = sum(
                request.env.user.partner_id.channel_member_ids.mapped("message_unread_counter"),
            )
        return values
