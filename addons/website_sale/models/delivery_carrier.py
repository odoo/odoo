# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.multi.mixin']

    website_description = fields.Text(
        string="Description for Online Quotations",
        related='product_id.description_sale',
        readonly=False,
    )
    is_pickup = fields.Boolean(compute='_compute_is_pickup')

    @api.depends('delivery_type')
    def _compute_is_pickup(self):
        for carrier in self:
            carrier.is_pickup = hasattr(carrier, f'{carrier.delivery_type}_use_locations') and getattr(carrier, f'{carrier.delivery_type}_use_locations')

    def _get_pickup_locations(self, zip_code=None, country=None, partner_id=None, **kwargs):
        """
        Return the pickup locations of the delivery method close to a given zip code.

        Use provided `zip_code` and `country` or the order's delivery address to determine the zip
        code and the country to use.

        Note: self.ensure_one()

        :param int zip_code: The zip code to look up to, optional.
        :param res.country country: The country to look up to, required if `zip_code` is provided.
        :param res.partner partner_id: The partner to use to get the address if no zip code is provided.
        :return: The close pickup locations data.
        :rtype: dict
        """
        self.ensure_one()
        partner_address = self.env['res.partner']
        if country:
            partner_address = self.env['res.partner'].new({
                'active': False,
                'country_id': country.id,
                'zip': zip_code,
            })
        elif partner_id:
            partner_address = partner_id
        try:
            error = {'error': _("No pick-up points are available for this delivery address.")}
            function_name = f'_{self.delivery_type}_get_close_locations'
            if not hasattr(self, function_name):
                return error
            pickup_locations = getattr(self, function_name)(partner_address, **kwargs)
            if not pickup_locations:
                return error
            return {'pickup_locations': pickup_locations}
        except UserError as e:
            return {'error': str(e)}
