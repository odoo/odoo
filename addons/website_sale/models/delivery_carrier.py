# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, models
from odoo.tools import OrderedSet
from odoo.tools.date_utils import localized
from odoo.tools.misc import format_date


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.multi.mixin']

    website_description = fields.Text(
        string="Description for Online Quotations",
        related='product_id.description_sale',
        readonly=False,
    )
    enable_delivery_estimate = fields.Boolean(
        string="Estimated Delivery",
        help="Display estimated date to your customer. Editable if range is defined.",
    )
    delivery_estimate_lead_days = fields.Integer()
    delivery_estimate_range_days = fields.Integer()
    delivery_calendar_id = fields.Many2one(comodel_name='resource.calendar', check_company=True)

    def _get_estimate_delivery_days(self):
        """Return the available days defined on the estimated delivery field based on the calendar.

        :returns: list of all available days in the estimated delivery range defined by
                  delivery_estimate_lead_days and delivery_estimate_range_days.
        :rtype: list
        """
        self.ensure_one()
        if self.enable_delivery_estimate:
            # `_attendance_intervals_batch` requires the datetime to be timezoned
            current_date = localized(fields.Datetime.now())
            max_range_days = self.delivery_estimate_lead_days + self.delivery_estimate_range_days
            # Add 30 days as a buffer to account for unavailable days.
            availabilities = self.delivery_calendar_id._attendance_intervals_batch(
                current_date, current_date + timedelta(days=max_range_days + 30)
            )[False]
            available_days = list(
                OrderedSet([availability[0].date().isoformat() for availability in availabilities])
            )
            return available_days[self.delivery_estimate_lead_days : max_range_days + 1]
        return []

    def _format_estimate_delivery_date(self, estimated_date):
        """Format a given estimated date to the MMM d, yyyy format.

        :returns: The formatted date.
        :rtype: str
        """
        return format_date(self.env, estimated_date, date_format='MMM d, yyyy')
