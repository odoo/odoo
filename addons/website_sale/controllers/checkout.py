# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.website_sale import const

class Checkout(PaymentPortal):

    # === CHECK METHODS === #

    def _check_cart(self, order_sudo):
        """Check that all the checkout steps prior to `href` are valid, otherwise redirect to the
        page where actions are still required.

        This is the main `_check_*` method to call.

        :param sale.order order_sudo: The current cart.
        :param str step_href: The url of the current `website.checkout.step`.
            Defaults to `request.httprequest.path`.
        :return: None if the user can be on the current step, otherwise a redirection.
        :rtype: None | http.Response
        """
        if redirection := self._check_mandatory(order_sudo):
            return redirection

        step_href = self._get_checkout_step_href(request.httprequest.path)
        previous_steps = request.website._get_previous_checkout_steps(step_href)

        for prev_step_href in previous_steps.mapped('step_href'):
            if redirection := self._check_checkout_step(prev_step_href, order_sudo):
                return redirection

    def _get_checkout_step_href(self, href):
        return const.CHECKOUT_STEP_HREF_MAPPING.get(href, href)

    def _check_mandatory(self, order_sudo):
        # NOTE: Im not sure about this being here. We have to keep in mind that the root call is
        # `_check_cart` which is not at all what this does. Either we rename `_check_cart`, which
        # im more in favor. Or each route should do the check.
        if not request.website.has_ecommerce_access():
            return request.redirect_query('/web/login', {'redirect': request.httprequest.full_path})

    def _check_checkout_step(self, step_href, order_sudo):
        """Check that the given step is finished and valid, otherwise redirect to the page where
        actions are still required.

        :param str step_href: The checkout step href to check.
        :param sale.order order_sudo: The current cart.
        :return: None if the given step is valid, otherwise a redirection to the appropriate page.
        :rtype: None | http.Response
        """
        return
