# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request

from odoo.addons.website_sale import const

class CheckoutValidation(Controller):

    # === CHECK METHODS === #

    def _check_checkout_step_access(self):
        """Check that all the checkout steps prior to the current step are valid, otherwise redirect
        to the page where actions are still required.

        Uses :attr:`request.httprequest.path` to find the current checkout step. See also
        :meth:`_get_checkout_step_href`.

        :return: None if the user can be on the current step, otherwise a redirection.
        :rtype: None | http.Response
        """
        order_sudo = request.cart
        if redirection := self._check_mandatory():
            return redirection

        step_href = self._get_checkout_step_href(request.httprequest.path)
        previous_steps = request.website._get_previous_checkout_steps(step_href)

        for prev_step_href in previous_steps.mapped('step_href'):
            if redirection := self._check_checkout_step(prev_step_href, order_sudo):
                return redirection

    def _get_checkout_step_href(self, href):
        return const.CHECKOUT_STEP_HREF_MAPPING.get(href, href)

    def _check_mandatory(self):
        if not request.website.has_ecommerce_access():
            return request.redirect_query('/web/login', {'redirect': request.httprequest.full_path})

    def _check_checkout_step(self, step_href, order_sudo):
        """Check that the given step is finished and valid, otherwise redirect to the page where
        actions are still required.

        This method is intended to be overriden by other modules

        :param str step_href: The checkout step href to check.
        :param sale.order order_sudo: The current cart.
        :return: None if the given step is valid, otherwise a redirection to the appropriate page.
        :rtype: None | http.Response
        """
        return
