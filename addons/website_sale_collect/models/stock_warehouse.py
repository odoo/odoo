# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.misc import format_duration


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    opening_hours = fields.Many2one(
        string="Opening Hours", comodel_name='resource.calendar', check_company=True
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
                wh_location.write({'partner_latitude': 1000, 'partner_longitude': 1000})

        # Format the pickup location values of the warehouse.
        try:
            pickup_location_values = {
                'id': self.id,
                'name': wh_location['name'],
                'street': wh_location['street'],
                'city': wh_location.city,
                'state': wh_location.state_id.code or '',
                'zip_code': wh_location.zip or '',
                'country_code': wh_location.country_code,
                'latitude': wh_location.partner_latitude,
                'longitude': wh_location.partner_longitude,
            }
        except AttributeError:
            return {}

        # Prepare the opening hours data.
        if self.opening_hours:
            opening_hours_dict = {str(i): [] for i in range(7)}
            for att in self.opening_hours.attendance_ids:
                if att.day_period in ('morning', 'afternoon', 'full_day'):
                    opening_hours_dict[att.dayofweek].append(
                        f'{format_duration(att.hour_from)} - {format_duration(att.hour_to)}'
                    )
            pickup_location_values['opening_hours'] = opening_hours_dict
        else:
            pickup_location_values['opening_hours'] = {}
        return pickup_location_values
