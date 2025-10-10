# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from pytz import timezone

from odoo import fields, models
from odoo.tools.misc import format_date, get_lang


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.multi.mixin']

    website_description = fields.Text(
        string="Description for Online Quotations",
        related='product_id.description_sale',
        readonly=False,
    )
    has_estimated_delivery = fields.Boolean(
        string='Estimated Delivery',
        help="Display estimated date to your customer. Editable if range is defined."
    )
    estimated_delivery_start = fields.Integer()
    estimated_delivery_end = fields.Integer()
    opening_hours = fields.Many2one(
        string="Opening Hours", comodel_name='resource.calendar', check_company=True
    )

    def _get_available_days(self):
        """Return the available days defined on the estimated delivery field based on the calendar.

        :returns: list of all available days of a given range.
        :rtype: list
        """
        self.ensure_one()
        available_days = []
        if self.has_estimated_delivery:
            # `_attendance_intervals_batch` requires the datetime to be timezoned
            tz = timezone(self.opening_hours.tz)
            current_date = fields.Datetime.now()
            # Find working days from the next day
            from_datetime = (current_date + timedelta(days=1)).astimezone(tz)
            # add 30 days as buffer to account for unavailable days
            to_datetime = (
                current_date + timedelta(days=self.estimated_delivery_end + 30)
            ).astimezone(tz)
            availabilities = self.opening_hours._attendance_intervals_batch(
                from_datetime, to_datetime)[False]._items
            for availability in availabilities:
                # availability is a tuple where the first element is the datetime object
                availability_date = availability[0].date()
                if availability_date not in available_days:
                    available_days.append(availability_date)
                if len(available_days) == self.estimated_delivery_end + self.estimated_delivery_start:
                    break
        # Return the availability starting from the estimated_delivery_start working days
        return available_days[self.estimated_delivery_start:]

    def _get_first_available_delivery_date(self):
        """Return the first available day for delivery called when `estimated_delivery_start`
        and `estimated_delivery_end` are equal so no need to return the full range of available
        days.

        :returns: list of all available days of a given range.
        :rtype: list
        """
        default_date = self._get_available_days()[0]
        lang_code = self.env.user.lang or get_lang(self.env).code
        return format_date(self.env, default_date, date_format='medium', lang_code=lang_code)
