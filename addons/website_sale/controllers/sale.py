# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website.tools import get_base_domain
from odoo.http import request


class CustomerPortal(sale_portal.CustomerPortal):
    def _get_portal_order_page_redirect(self, order_sudo):
        redirect = super()._get_portal_order_page_redirect(order_sudo)
        if redirect:
            return redirect

        website = order_sudo._get_portal_website()
        if (
            website.domain
            and request.httprequest.environ.get('HTTP_HOST', '') != get_base_domain(website.domain)
        ):
            url = tools.urls.urljoin(website.domain, request.httprequest.full_path)
            return request.redirect(url)
        return None

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
