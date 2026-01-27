from odoo.fields import Domain
from odoo.http import Controller, request


class Checkout(Controller):

    # === CHECK METHODS === #

    def _validate_previous_checkout_steps(self, *, step_href=None, **kwargs):
        """Check that the checkout steps prior to the current step are valid; otherwise,
        redirect to the page where actions are still required.

        Note: prior checkout steps, including non-published steps.

        :param str step_href: The current step href. Defaults to `request.httprequest.path`.
        :param dict kwargs: Additional arguments, forwarded to `_check_post_checkout_step`.
        :return: None if the user can be on the current step; otherwise, a redirection.
        :rtype: None | http.Response
        """
        website = request.website
        step_href = step_href or request.env['ir.http'].url_unrewrite(
            request.httprequest.path, website.id
        )

        current_step = website._get_checkout_step(step_href)
        previous_steps = current_step._get_previous_checkout_steps(
            Domain('website_id', '=', website.id)
        )

        for previous_step in previous_steps.sorted('sequence'):
            if redirection := self._check_post_checkout_step(
                previous_step.step_href, request.cart, **kwargs
            ):
                return redirection

    def _check_post_checkout_step(self, step_href, order_sudo, /, **kwargs):
        """Perform necessary checks against the current cart after the given checkout step and
        redirect to the page where actions are still required.

        This method is intended to be overridden by other modules if further validation is needed
        after specific steps.

        :param str step_href: The checkout step href that has already been completed.
        :param sale.order order_sudo: The current cart.
        :param dict kwargs: Additional arguments.
        :return: None if the given step is valid; otherwise, a redirection to the appropriate page.
        :rtype: None | http.Response
        """
