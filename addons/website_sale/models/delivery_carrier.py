# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
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
    has_estimated_delivery = fields.Boolean(
        string="Estimated Delivery",
        help="Display estimated date to your customer. Editable if range is defined.",
    )
    estimated_delivery_min_days = fields.Integer()
    estimated_delivery_max_days = fields.Integer()
    opening_hours = fields.Many2one(comodel_name='resource.calendar', check_company=True)

    @api.constrains('estimated_delivery_min_days', 'estimated_delivery_max_days')
    def _check_margin(self):
        if any(dm.estimated_delivery_min_days > dm.estimated_delivery_max_days for dm in self):
            raise ValidationError(self.env._(
                "The start date of the estimated delivery should be smaller than the end date."
            ))

    def _get_available_days(self):
        """Return the available days defined on the estimated delivery field based on the calendar.

        :returns: list of all available days in the estimated delivery range defined by
                  estimated_delivery_min_days and estimated_delivery_max_days.
        :rtype: list
        """
        self.ensure_one()
        if self.has_estimated_delivery:
            # `_attendance_intervals_batch` requires the datetime to be timezoned
            current_date = localized(fields.Datetime.now())
            from_datetime = current_date
            # add 30 days as buffer to account for unavailable days
            to_datetime = current_date + timedelta(days=self.estimated_delivery_max_days + 30)
            availabilities = self.opening_hours._attendance_intervals_batch(
                from_datetime, to_datetime)[False]
            available_days = list(
                OrderedSet([availability[0].date().isoformat() for availability in availabilities])
            )
            return available_days[
                self.estimated_delivery_min_days : self.estimated_delivery_max_days + 1
            ]
        return []

    def _get_first_available_delivery_date(self):
        """Return the first available day for delivery called when `estimated_delivery_min_days`
        and `estimated_delivery_max_days` are equal.

        :returns: The first available day.
        :rtype: str
        """
        if estimated_delivery_date := self._get_available_days():
            default_date = estimated_delivery_date[0]
            return format_date(self.env, default_date, date_format='MMM d, yyyy')
        return ""
