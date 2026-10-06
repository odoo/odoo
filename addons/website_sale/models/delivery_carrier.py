# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import OrderedSet
from odoo.tools.date_utils import localized
from odoo.tools.misc import format_date

from odoo.addons.website_sale.const import DELIVERY_ESTIMATE_MARGIN_DAYS


class DeliveryCarrier(models.Model):
    _name = "delivery.carrier"
    _inherit = ["delivery.carrier", "website.published.multi.mixin"]

    website_description = fields.Text(string="Description for Online Quotations", translate=True)
    delivery_estimate_mode = fields.Selection(
        string="Estimated Delivery",
        help="Display an estimated date to your customer. With 'User Choice', the customer picks a"
        " date inside the defined range.",
        selection=[("none", "None"), ("fixed", "Fixed"), ("user_choice", "User Choice")],
        default="none",
        required=True,
    )
    delivery_estimate_min_days = fields.Integer()
    delivery_estimate_max_days = fields.Integer(
        compute="_compute_delivery_estimate_max_days", store=True, readonly=False
    )
    delivery_calendar_id = fields.Many2one(comodel_name="resource.calendar", check_company=True)

    _check_delivery_estimate_min_days = models.Constraint(
        "CHECK (delivery_estimate_min_days >= 0)", "The number of delivery days can't be negative"
    )

    _check_delivery_estimate_max_days = models.Constraint(
        "CHECK ("
        "    delivery_estimate_mode = 'none'"
        "    OR delivery_estimate_max_days >= delivery_estimate_min_days"
        ")",
        "The delivery can't end before it starts.",
    )

    @api.depends("delivery_estimate_mode", "delivery_estimate_min_days")
    def _compute_delivery_estimate_max_days(self):
        """Set the maximum to the minimum in 'Fixed' mode, as the range is a single day."""
        for carrier in self.filtered(lambda c: c.delivery_estimate_mode == "fixed"):
            carrier.delivery_estimate_max_days = carrier.delivery_estimate_min_days

    def write(self, vals):
        """Reset estimated delivery settings if delivery type is incompatible."""
        if (
            "delivery_type" in vals
            and vals["delivery_type"] not in self._get_delivery_estimate_supported_types()
        ):
            vals.update({
                "delivery_estimate_mode": "none",
                "delivery_estimate_min_days": 0,
                "delivery_estimate_max_days": 0,
                "delivery_calendar_id": None,
            })
        return super().write(vals)

    def _get_delivery_estimate_supported_types(self):
        """Return the delivery types on which an estimated delivery date can be configured.

        :returns: The supported delivery types.
        :rtype: list[str]
        """
        return ["fixed", "base_on_rule"]

    def _get_delivery_estimate_dates(self, order=None):
        """Return the days of the estimated delivery range that the customer can be delivered on.

        The range is defined by delivery_estimate_min_days and delivery_estimate_max_days.

        :param sale.order order: The order to deliver, if any.
        :returns: The days of the range, in the ISO format, oldest first.
        :rtype: list
        """
        self.ensure_one()
        if self.delivery_estimate_mode == "none":
            return []

        available_days = self._get_calendar_available_days(order=order)
        return available_days[self.delivery_estimate_min_days : self.delivery_estimate_max_days + 1]

    def _get_calendar_available_days(self, order=None):
        """Return the days the delivery method can deliver on, from today.

        Hook for the delivery types that don't deliver according to `delivery_calendar_id`.

        :param sale.order order: The order to deliver, if any.
        :returns: The available days, in the ISO format, oldest first.
        :rtype: list
        """
        self.ensure_one()

        utc_now = localized(fields.Datetime.now())  # `_work_intervals_batch` requires a timezone
        utc_end = utc_now + timedelta(
            days=self.delivery_estimate_max_days + DELIVERY_ESTIMATE_MARGIN_DAYS
        )
        availabilities = self.delivery_calendar_id._work_intervals_batch(utc_now, utc_end)[False]
        return list(
            OrderedSet(availability[0].date().isoformat() for availability in availabilities)
        )

    def _format_delivery_estimate_date(self, estimated_date):
        """Format a given estimated date to the MMM d, yyyy format.

        :returns: The formatted date.
        :rtype: str
        """
        return format_date(self.env, estimated_date, date_format="MMM d, yyyy")
