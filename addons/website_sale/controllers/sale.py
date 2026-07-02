# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):
    @route()
    def portal_order_page(self, *args, **kw):
        order_id = kw.get("order_id")
        if website := self.env["sale.order"].sudo().browse(order_id).assigned_website_id:
            request.update_context(website_id=website.id)
            website._force()

        return super().portal_order_page(*args, **kw)

    def _get_payment_values(self, order_sudo, website_id=None, **kwargs):
        """Override of `sale` to inject the `website_id` into the kwargs.

        :param sale.order order_sudo: The sales order being paid.
        :param int website_id: The website on which the order was made, if any, as a `website` id.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The payment-specific values.
        :rtype: dict
        """
        if not website_id:
            if order_sudo.website_id:
                website_id = order_sudo.website_id.id
            elif website := self.env.website:
                website_id = website.id

        return super()._get_payment_values(order_sudo, website_id=website_id, **kwargs)
