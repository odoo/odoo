# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.website_sale_collect import utils


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('in_store', "Pick up in store")], ondelete={'in_store': 'set default'}
    )
    warehouse_ids = fields.Many2many(string="Stores", comodel_name='stock.warehouse')
    delivery_method = fields.Selection(selection_add=([('in_store', 'Pick up in store')]))

    def _compute_delivery_method(self):
        super()._compute_delivery_method()
        for carrier in self:
            if carrier.delivery_type == 'in_store':
                carrier.delivery_method = 'in_store'

    def _compute_is_pickup(self):
        super()._compute_is_pickup()
        for carrier in self:
            if carrier.delivery_type == 'in_store':
                carrier.is_pickup = True

    @api.constrains('delivery_type', 'is_published', 'warehouse_ids')
    def _check_in_store_dm_has_warehouses_when_published(self):
        if any(self.filtered(
            lambda dm: dm.delivery_type == 'in_store'
            and dm.is_published
            and not dm.warehouse_ids
        )):
            raise ValidationError(
                _("The delivery method must have at least one warehouse to be published.")
            )

    @api.constrains('delivery_type', 'company_id', 'warehouse_ids')
    def _check_warehouses_have_same_company(self):
        for dm in self:
            if dm.delivery_type == 'in_store' and dm.company_id and any(
                wh.company_id and dm.company_id != wh.company_id for wh in dm.warehouse_ids
            ):
                raise ValidationError(
                    _("The delivery method and a warehouse must share the same company")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('delivery_type') == 'in_store':
                vals['integration_level'] = 'rate'
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('delivery_type') == 'in_store':
            vals['integration_level'] = 'rate'
        return super().write(vals)

    # === BUSINESS METHODS ===#

    def _get_pickup_locations(self, zip_code=None, country=None, **kwargs):
        """ Override of `website_sale` to ensure that a country is provided when there is a zip
        code.

        If the country cannot be found (e.g., the GeoIP request fails), the zip code is cleared to
        prevent the parent method's assertion to fail.
        """
        if zip_code and not country:
            country_code = None
            shipping_address = self.env['res.partner']
            if kwargs.get('parent_record'):
                shipping_address = kwargs.get('parent_record').partner_id
            if shipping_address.location_data:
                country_code = shipping_address.location_data['country_code']
            elif request.geoip.country_code:
                country_code = request.geoip.country_code
            country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
            if not country:
                zip_code = None  # Reset the zip code to skip the `assert` in the `super` call.
        return super()._get_pickup_locations(zip_code=zip_code, country=country, **kwargs)

    def _in_store_get_close_locations(self, partner_address, product_id=None, parent_record=None):
        """ Get the formatted close pickup locations sorted by distance to the partner address.

        :param res.partner partner_address: The address to use to sort the pickup locations.
        :param str product_id: The product whose product page was used to open the location
                               selector, if any, as a `product.product` id.
        :return: The sorted and formatted close pickup locations.
        :rtype: list[dict]
        """
        try:
            product_id = product_id and int(product_id)
        except ValueError:
            product = self.env['product.product']
        else:
            product = self.env['product.product'].browse(product_id)

        partner_address.geo_localize()  # Calculate coordinates.

        pickup_locations = []
        record = parent_record or request.cart
        for wh in self.warehouse_ids:
            pickup_location_values = wh._prepare_pickup_location_data()
            if not pickup_location_values:  # Ignore warehouses with badly configured addresses.
                continue

            # Prepare the stock data based on either the product or the order.
            if product:  # Called from the product page.
                in_store_stock_data = utils.format_product_stock_values(product, wh.id)
            else:  # Called from the checkout page.
                in_store_stock_data = {'in_stock': record._is_in_stock(wh.id)}

            # Calculate the distance between the partner address and the warehouse location.
            pickup_location_values.update({
                'additional_data': {'in_store_stock_data': in_store_stock_data},
                'distance': utils.calculate_partner_distance(partner_address, wh.partner_id),
            })
            pickup_locations.append(pickup_location_values)

        return sorted(pickup_locations, key=lambda k: k['distance'])

    def in_store_rate_shipment(self, *_args):
        return {
            'success': True,
            'price': self.product_id.list_price,
            'error_message': False,
            'warning_message': False,
        }
