
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class PickupLocationMixin(models.AbstractModel):
    """ This mixin should be inherited by any model that needs to be able to
    work with the pickup location selector.
    It assumes that the model inheriting it has the following fields:
    * M2O field named `carrier_id` related to `delivery.carrier` model.
    * M2O field named `partner_id` related to `res.partner` model (used to retrieve close locations if present).
    It also must override the method `_get_pickup_point_address_field_name`
    which should return the name of the field that stores the pickup point address. The field must be a M2O related to `res.partner`.
    """
    _name = 'pickup.location.mixin'
    _description = 'Pickup Location Mixin'

    def action_open_pickup_location_selector(self):
        """ Open the pickup location selector wizard.
        """
        self.ensure_one()
        if not self.carrier_id.is_pickup:
            raise UserError(_('This shipping method does not support pickup points.'))
        return {
            'name': _('Select a Pickup Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'pickup.location.selector',
            'view_mode': 'form',
            'view_id': self.env.ref('delivery.pickup_location_selector_view_form').id,
            'target': 'new',
            'context': {
                'default_parent_model': self._name,
                'default_parent_id': self.id,
                'default_zip_code': self.partner_id.zip,
            },
        }

    def _set_pickup_location(self, pickup_location_data):
        """ Set the pickup location on the current record.
        """
        self.ensure_one()
        if self.carrier_id.is_pickup:
            address = self.env['res.partner']._address_from_json(pickup_location_data, self.partner_id)
            self[self._get_pickup_point_address_field_name()] = address

    def _get_pickup_locations(self, zip_code=None, country=None, **kwargs):
        """ Return the pickup locations of the delivery method close to a given zip code.

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
            pickup_locations = getattr(self.carrier_id, function_name)(partner_address, **kwargs)
            if not pickup_locations:
                return error
            return {'pickup_locations': pickup_locations}
        except UserError as e:
            return {'error': str(e)}

    def _get_pickup_point_address_field_name(self):
        """ Return the name of the field that stores the delivery address.
        Must be overridden by any model that inherits this mixin. """
        return ''
