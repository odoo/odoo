from odoo import fields, models
from odoo.tools.misc import format_duration


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    opening_hours = fields.Many2one(
        comodel_name="resource.calendar",
        check_company=True,
    )

    def _update_missing_coordinates(self):
        def are_coordinates_missing(loc_):
            return (loc_.partner_latitude, loc_.partner_longitude) == (0, 0)

        for warehouse in self:
            wh_location = warehouse.partner_id
            if are_coordinates_missing(wh_location):
                wh_location.geo_localize()
                if are_coordinates_missing(wh_location):
                    wh_location.write(
                        {"partner_latitude": 1000, "partner_longitude": 1000}
                    )

    def _prepare_pickup_location_data(self):
        wh_location = self.partner_id
        try:
            pickup_location_values = {
                "id": self.id,
                "name": wh_location["name"].title(),
                "street": wh_location["street"].title(),
                "city": wh_location.city.title(),
                "state": wh_location.state_id.code or "",
                "zip_code": wh_location.zip or "",
                "country_code": wh_location.country_code,
                "latitude": wh_location.partner_latitude,
                "longitude": wh_location.partner_longitude,
            }
        except AttributeError:
            return {}

        if self.opening_hours:
            opening_hours_dict = {str(i): [] for i in range(7)}
            for att in self.opening_hours.attendance_ids:
                if att.day_period in ("morning", "afternoon", "full_day"):
                    opening_hours_dict[att.dayofweek].append(
                        f"{format_duration(att.hour_from)} - {format_duration(att.hour_to)}"
                    )
            pickup_location_values["opening_hours"] = opening_hours_dict
        else:
            pickup_location_values["opening_hours"] = {}
        return pickup_location_values
