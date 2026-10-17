# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import OrderedSet
from odoo.tools.date_utils import localized
from odoo.tools.misc import format_date

UNAVAILABLE_DAYS_BUFFER = 30


class DeliveryCarrier(models.Model):
    _name = "delivery.carrier"
    _inherit = ["delivery.carrier", "website.published.multi.mixin"]

    website_description = fields.Text(
        string="Description for Online Quotations",
        related="product_id.description_sale",
        readonly=False,
    )
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

    @api.depends("delivery_estimate_mode", "delivery_estimate_min_days")
    def _compute_delivery_estimate_max_days(self):
        """Raise the maximum to the fixed day when below it so that switching to 'User Choice'
        starts from a valid range, while keeping a maximum already set in 'User Choice'."""
        for carrier in self.filtered(
            lambda c: (
                c.delivery_estimate_mode == "fixed"
                and c.delivery_estimate_max_days < c.delivery_estimate_min_days
            )
        ):
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

    _check_delivery_estimate_min_days = models.Constraint(
        "CHECK (delivery_estimate_min_days >= 0)", "The number of delivery days can't be negative"
    )

    _check_delivery_estimate_max_days = models.Constraint(
        "CHECK ("
        "    delivery_estimate_mode != 'user_choice'"
        "    OR delivery_estimate_max_days >= delivery_estimate_min_days"
        ")",
        "The delivery range should be from min to max number of days.",
    )

    def _get_estimate_delivery_days(self, order=None):
        """Return the days of the estimated delivery range that the customer can be delivered on.

        The range is defined by delivery_estimate_min_days and delivery_estimate_max_days.

        :param sale.order order: The order to deliver, if any.
        :returns: The days of the range, in the ISO format, oldest first.
        :rtype: list
        """
        self.ensure_one()
        if self.delivery_estimate_mode == "none":
            return []

        last_day = self.delivery_estimate_min_days
        if self.delivery_estimate_mode == "user_choice":
            last_day = self.delivery_estimate_max_days

        available_days = self._get_calendar_available_days(order=order)
        return available_days[self.delivery_estimate_min_days : last_day + 1]

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
            days=self.delivery_estimate_max_days + UNAVAILABLE_DAYS_BUFFER
        )
        availabilities = self.delivery_calendar_id._work_intervals_batch(utc_now, utc_end)[False]
        return list(
            OrderedSet(availability[0].date().isoformat() for availability in availabilities)
        )

    def _format_estimate_delivery_date(self, estimated_date):
        """Format a given estimated date to the MMM d, yyyy format.

        :returns: The formatted date.
        :rtype: str
        """
        return format_date(self.env, estimated_date, date_format="MMM d, yyyy")
