# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):

    def _get_payment_values(self, order_sudo, website_id=None, **kwargs):
        """ Override of `sale` to inject the `website_id` into the kwargs.

        :param sale.order order_sudo: The sales order being paid.
        :param int website_id: The website on which the order was made, if any, as a `website` id.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The payment-specific values.
        :rtype: dict
        """
        website_id = website_id or order_sudo.website_id.id
        return super()._get_payment_values(order_sudo, website_id=website_id, **kwargs)
