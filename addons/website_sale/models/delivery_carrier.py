# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, models
from odoo.tools import OrderedSet
from odoo.tools.date_utils import localized
from odoo.tools.misc import format_date


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
    delivery_estimate_max_days = fields.Integer()
    delivery_calendar_id = fields.Many2one(comodel_name="resource.calendar", check_company=True)

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

        first_day = last_day = self.delivery_estimate_min_days
        if self.delivery_estimate_mode == "user_choice":
            last_day = self.delivery_estimate_max_days

        calendar, open_every_day = self._get_calendar_for_estimate(order=order)
        if not calendar and not open_every_day:
            return []

        now = fields.Datetime.now()
        if calendar:
            # `_work_intervals_batch` requires the datetime to be timezoned
            utc_now = localized(now)
            # Add 30 days as a buffer to account for unavailable days.
            utc_end = utc_now + timedelta(days=last_day + 30)
            availabilities = calendar._work_intervals_batch(utc_now, utc_end)[False]
            available_days = list(
                OrderedSet([availability[0].date().isoformat() for availability in availabilities])
            )
        else:
            available_days = [
                (now.date() + timedelta(days=day)).isoformat() for day in range(last_day + 1)
            ]

        return available_days[first_day : last_day + 1]

    def _get_calendar_for_estimate(self, order=None):
        """Return the calendar to compute the estimated delivery days with.

        When a calendar is returned, it is used regardless of the flag.

        :param sale.order order: The order to deliver, if any.
        :returns: The calendar, and whether every day is deliverable when there is no calendar.
        :rtype: tuple[resource.calendar, bool]
        """
        self.ensure_one()
        return self.delivery_calendar_id, False

    def _format_estimate_delivery_date(self, estimated_date):
        """Format a given estimated date to the MMM d, yyyy format.

        :returns: The formatted date.
        :rtype: str
        """
        return format_date(self.env, estimated_date, date_format="MMM d, yyyy")
