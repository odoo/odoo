# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
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
    enable_delivery_estimate = fields.Selection(
        string="Estimated Delivery",
        help="Display an estimated date to your customer. With 'User Choice', the customer picks a"
        " date inside the defined range.",
        selection=[("none", "None"), ("fixed", "Fixed"), ("user_choice", "User Choice")],
        default="none",
        required=True,
    )
    delivery_estimate_lead_days = fields.Integer()
    delivery_estimate_end_days = fields.Integer()
    delivery_calendar_id = fields.Many2one(comodel_name="resource.calendar", check_company=True)

    @api.constrains(
        "enable_delivery_estimate", "delivery_estimate_lead_days", "delivery_estimate_end_days"
    )
    def _check_delivery_estimate_days(self):
        for carrier in self:
            if carrier.enable_delivery_estimate != "none":
                if carrier.delivery_estimate_lead_days < 0:
                    raise ValidationError(
                        self.env._("The number of working days can't be negative.")
                    )
                if carrier.enable_delivery_estimate == "user_choice":
                    if carrier.delivery_estimate_end_days < carrier.delivery_estimate_lead_days:
                        raise ValidationError(
                            self.env._(
                                "The delivery range should be from min to max number of days."
                            )
                        )
                    if carrier.delivery_estimate_end_days < 0:
                        raise ValidationError(
                            self.env._("The number of working days can't be negative.")
                        )

    def _get_estimate_delivery_days(self, order=None):
        """Return the days of the estimated delivery range that the customer can be delivered on.

        The range is defined by delivery_estimate_lead_days and delivery_estimate_end_days.

        :param sale.order order: The order to deliver, if any.
        :returns: The days of the range, in the ISO format, oldest first.
        :rtype: list
        """
        self.ensure_one()
        if self.enable_delivery_estimate == "none":
            return []
        first_day = self.delivery_estimate_lead_days
        # A fixed estimate always resolves to a single day
        last_day = (
            self.delivery_estimate_end_days
            if self.enable_delivery_estimate == "user_choice"
            else first_day
        )
        return self._get_deliverable_days(last_day, order=order)[first_day : last_day + 1]

    def _get_deliverable_days(self, last_day, order=None):
        """Return the days on which the delivery method can deliver, from today on.

        :param int last_day: The last day to return, counted in days from today.
        :param sale.order order: The order to deliver, if any.
        :returns: The deliverable days, in the ISO format, oldest first.
        :rtype: list
        """
        self.ensure_one()
        return self._get_calendar_days(self.delivery_calendar_id, last_day)

    def _get_calendar_days(self, calendar, last_day):
        """Return the working days of the calendar, from today on.

        :param resource.calendar calendar: The working schedule to get the working days of.
        :param int last_day: The last day to return, counted in days from today.
        :returns: The working days, in the ISO format, oldest first.
        :rtype: list
        """
        if not calendar:
            return []
        # `_attendance_intervals_batch` requires the datetime to be timezoned
        current_date = localized(fields.Datetime.now())
        # Add 30 days as a buffer to account for unavailable days.
        availabilities = calendar._work_intervals_batch(
            current_date, current_date + timedelta(days=last_day + 30)
        )[False]
        return list(
            OrderedSet([availability[0].date().isoformat() for availability in availabilities])
        )

    def _format_estimate_delivery_date(self, estimated_date):
        """Format a given estimated date to the MMM d, yyyy format.

        :returns: The formatted date.
        :rtype: str
        """
        return format_date(self.env, estimated_date, date_format="MMM d, yyyy")
