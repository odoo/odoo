# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.tools import format_date
from odoo.tools.misc import format_duration

EXCEPTIONAL_CLOSING_DATES_LOOKUP_DAYS = 60


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    opening_hours = fields.Many2one(
        string="Opening Hours", comodel_name="resource.calendar", check_company=True
    )

    def _prepare_pickup_location_data(self):

        def are_coordinates_missing(loc_):
            return (loc_.partner_latitude, loc_.partner_longitude) == (0, 0)

        # Find the longitude and latitude of the warehouse.
        wh_location = self.partner_id
        if are_coordinates_missing(wh_location):
            wh_location.geo_localize()
            if are_coordinates_missing(wh_location):  # Geolocation failed.
                # Assign invalid coordinates to skip future geolocation attempts. As coordinates are
                # only updated when *both* latitude and longitude are zero, this prevents a spam of
                # OpenStreetMap's API when warehouses with an invalid address are loaded in the
                # location selector of Click and Collect.
                wh_location.write({"partner_latitude": 1000, "partner_longitude": 1000})

        # Format the pickup location values of the warehouse.
        try:
            pickup_location_values = {
                "id": self.id,
                "name": wh_location["name"],
                "street": wh_location["street"] or "",
                "city": wh_location.city or "",
                "state": wh_location.state_id.code or "",
                "zip_code": wh_location.zip or "",
                "country_code": wh_location.country_code,
                "latitude": wh_location.partner_latitude,
                "longitude": wh_location.partner_longitude,
            }
        except AttributeError:
            return {}

        # Prepare the opening hours data.
        if self.opening_hours:
            opening_hours_dict = {str(i): [] for i in range(7)}
            for att in self.opening_hours.attendance_ids:
                opening_hours_dict[att.dayofweek].append(
                    f"{format_duration(att.hour_from)} - {format_duration(att.hour_to)}"
                )
            pickup_location_values["opening_hours"] = opening_hours_dict
            pickup_location_values["closing_dates"] = self._get_exceptional_closing_dates()
        else:
            pickup_location_values["opening_hours"] = {}
            pickup_location_values["closing_dates"] = []
        return pickup_location_values

    def _get_exceptional_closing_dates(self):
        """Return the warehouse's exceptional closing periods.

        :return: The exceptional closing periods, one per closing leave, sorted chronologically.
        :rtype: list[dict]
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        limit_date = today + timedelta(days=EXCEPTIONAL_CLOSING_DATES_LOOKUP_DAYS)
        tz = ZoneInfo(self.opening_hours.company_id.tz or self.env.company.tz or "UTC")
        leaves = self.opening_hours.global_leave_ids.filtered(
            lambda leave: leave.count_as == "absence"
        ).sorted("date_from")
        closing_periods = []
        for leave in leaves:
            date_from = leave.date_from.replace(tzinfo=UTC).astimezone(tz).date()
            date_to = leave.date_to.replace(tzinfo=UTC).astimezone(tz).date()
            if date_to < today or date_from > limit_date:
                continue
            closing_periods.append({
                "date_from": format_date(self.env, date_from),
                "date_to": format_date(self.env, date_to),
            })
        return closing_periods
