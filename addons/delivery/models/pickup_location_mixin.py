
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models, _
from odoo.exceptions import UserError


class PickupLocationMixin(models.AbstractModel):
    """ This mixin should be inherited by any model that needs to be able to
    work with the pickup location selector.
    It assumes that the model inheriting it has the following fields:
    * M2O field named `carrier_id` related to `delivery.carrier` model.
    * M2O field named `partner_id` related to `res.partner` model (used to retrieve close locations if present).
    """
    _name = 'pickup.location.mixin'
    _description = 'Pickup Location Mixin'

    def _get_delivery_address_field(self):
        """ Get the field name to store the delivery address. """
        return 'partner_shipping_id'

    def set_pickup_location(self, pickup_location_data):
        """ Set the pickup location on the current record. """
        self.ensure_one()
        if self.carrier_id.is_pickup:
            pickup_location_data = json.loads(pickup_location_data)
            parent_location = self[self._get_delivery_address_field()].parent_id if self[self._get_delivery_address_field()].is_pickup_location else self.partner_id
            address = self.env['res.partner']._address_from_json(pickup_location_data, parent_location)
            self[self._get_delivery_address_field()] = address or self.partner_id

    def _get_pickup_locations(self, zip_code=None, country=None, **kwargs):
        """
        Return the pickup locations of the delivery method close to a given zip code.

        Use provided `zip_code` and `country` or the order's delivery address to determine the zip
        code and the country to use.

        Note: self.ensure_one()

        :param int zip_code: The zip code to look up to, optional.
        :param res.country country: The country to look up to, required if `zip_code` is provided.
        :return: The close pickup locations data.
        :rtype: dict
        """
        self.ensure_one()
        if zip_code:
            assert country  # country is required if zip_code is provided.
            partner_address = self.env['res.partner'].new({
                'active': False,
                'country_id': country.id,
                'zip': zip_code,
            })
        else:
            partner_address = self.partner_id
        try:
            error = {'error': _("No pick-up points are available for this delivery address.")}
            function_name = f'_{self.carrier_id.delivery_type}_get_close_locations'
            if not hasattr(self.carrier_id, function_name):
                return error
            pickup_locations = getattr(self.carrier_id, function_name)(partner_address, parent_record=self, **kwargs)
            if not pickup_locations:
                return error
            return {'pickup_locations': pickup_locations}
        except UserError as e:
            return {'error': str(e)}
