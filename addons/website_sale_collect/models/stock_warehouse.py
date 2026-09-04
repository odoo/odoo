# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.tools.misc import OrderedSet, format_duration

from odoo.addons.website_sale_collect import const


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    opening_hours = fields.Many2one(
        string="Opening Hours", comodel_name="resource.calendar", check_company=True
    )

    def _prepare_pickup_location_data(self, **kwargs):

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

        pickup_location_values.update(self._prepare_pickup_availability_data(**kwargs))
        return pickup_location_values

    def _prepare_pickup_availability_data(self, estimated_dates=None):
        """Return the warehouse's opening information for click and collect widget.

        :param list[date] estimated_dates: The candidate dates to check, in chronological order.
        :return: Opening status information.
        :rtype: dict
        """
        self.ensure_one()
        result = {
            "opening_hours": {},
            "next_open_date": False,
            "closing_dates": [],
        }
        if self.opening_hours:
            tz = ZoneInfo(self.opening_hours.company_id.tz or self.env.company.tz or "UTC")
            result.update({
                "opening_hours": self._format_opening_hours(),
                "next_open_date": self._get_pickup_next_open_date(
                    tz, estimated_dates=estimated_dates
                ),
                "closing_dates": self._get_exceptional_closing_dates(tz),
            })
        return result

    def _format_opening_hours(self):
        """Return the warehouse's opening hours, formatted per day of the week.

        :return: A dict mapping each day of the week to a list of formatted attendance periods.
        :rtype: dict
        """
        self.ensure_one()
        opening_hours_dict = {str(i): [] for i in range(7)}
        for att in self.opening_hours.attendance_ids:
            opening_hours_dict[att.dayofweek].append(
                f"{format_duration(att.hour_from)} - {format_duration(att.hour_to)}"
            )
        return opening_hours_dict

    def _get_pickup_next_open_date(self, tz, estimated_dates=None):
        """Return the next date the warehouse is open.

        :param ZoneInfo tz: The warehouse's timezone.
        :param list[date] estimated_dates: Candidate dates to check for the earliest one the
                                           warehouse is open on, in chronological order.
        :return: The next open date, or `False` if none is found.
        :rtype: str | False
        """
        self.ensure_one()
        next_open_date = False
        now = datetime.now(UTC).astimezone(tz)
        limit_date = now + timedelta(days=const.OPENING_HOURS_LOOKUP_DAYS)
        work_intervals = self.opening_hours._work_intervals_batch(now, limit_date)[False]
        working_dates = OrderedSet(start.astimezone(tz).date() for start, *_ in work_intervals)

        if estimated_dates:  # Take into account the estimated delivery dates
            candidate_dates = OrderedSet(day for day in working_dates if day >= estimated_dates[0])
            if candidate_dates:
                next_open_date = next(iter(
                    candidate_dates & estimated_dates or candidate_dates)
                ).isoformat()
        elif working_dates:
            first_interval = next(iter(work_intervals))
            is_open_now = first_interval[0] <= now
            next_open_date = not is_open_now and next(iter(working_dates)).isoformat()
        return next_open_date

    def _get_exceptional_closing_dates(self, tz):
        """Return the warehouse's upcoming exceptional closing periods.

        :param ZoneInfo tz: The warehouse's timezone.
        :return: The exceptional closing periods, one per closing leave, sorted chronologically.
        :rtype: list[dict]
        """
        self.ensure_one()
        now_utc = fields.Datetime.now()
        limit_utc = now_utc + timedelta(days=const.OPENING_HOURS_LOOKUP_DAYS)
        leaves = self.opening_hours.global_leave_ids.filtered(
            lambda leave: (
                leave.count_as == "absence"
                and leave.date_to >= now_utc
                and leave.date_from <= limit_utc
            )
        ).sorted("date_from")
        return [
            {
                "date_from": leave.date_from.replace(tzinfo=UTC).astimezone(tz).date().isoformat(),
                "date_to": leave.date_to.replace(tzinfo=UTC).astimezone(tz).date().isoformat(),
            }
            for leave in leaves
        ]
