# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):
    @route()
    def portal_order_page(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            order_sudo = None

        if order_sudo and (website := order_sudo.assigned_website_id):
            request.update_context(website_id=website.id)
            website._force()

        return super().portal_order_page(order_id, access_token=access_token, **kw)
