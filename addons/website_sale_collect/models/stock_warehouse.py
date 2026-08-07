# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.misc import format_duration


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    opening_hours = fields.Many2one(
        string="Opening Hours", comodel_name="resource.calendar", check_company=True
    )

    def _prepare_pickup_location_data(self):
        wh_location = self.partner_id

        coordinates_are_missing = (
            wh_location.partner_latitude == 0 and wh_location.partner_longitude == 0
        )

        if coordinates_are_missing and not wh_location.geo_localization_failed:
            wh_location.geo_localize()

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
        else:
            pickup_location_values["opening_hours"] = {}
        return pickup_location_values
