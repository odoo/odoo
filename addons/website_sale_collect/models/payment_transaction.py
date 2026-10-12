# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import models
from odoo.tools.misc import format_date


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_status_message(self, *, order=None, **kwargs):
        """Override of `payment` to add a custom message for click & collect.

        :param sale.order order: The current cart linked to the transaction.
        """
        status_message = super()._get_status_message(order=order, **kwargs)
        if (
            order
            and order.website_id
            and self.provider_id.custom_mode == "on_site"
        ):
            if (
                commitment_date := order.commitment_date
            ) and order.commitment_date.date() != order.date_order.date():
                formatted_date = format_date(self.env, commitment_date)
                return Markup("<p>%s</p>") % self.env._(
                    "Your order will be ready on %s.", formatted_date
                )
        return status_message
