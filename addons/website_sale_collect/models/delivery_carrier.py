# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.misc import format_duration

from odoo.addons.website_sale_collect import utils


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('in_store', "Pick up in store")], ondelete={'in_store': 'set default'}
    )
    warehouse_ids = fields.Many2many(string="Stores", comodel_name='stock.warehouse')

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

    def _in_store_get_close_locations(self, partner_address, product_id=None):
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
        order_sudo = request.website.sale_get_order()
        for wh in self.warehouse_ids:
            # Prepare the stock data based on either the product or the order.
            if product:  # Called from the product page.
                in_store_stock_data = utils.format_product_stock_values(product, wh.id)
            else:  # Called from the checkout page.
                in_store_stock_data = {'in_stock': order_sudo._is_in_stock(wh.id)}

            # Prepare the warehouse location.
            wh_location = wh.partner_id
            if not wh_location.partner_latitude or not wh_location.partner_longitude:
                wh_location.geo_localize()  # Find the longitude and latitude of the warehouse.

            # Format the pickup location values of the warehouse.
            try:
                pickup_location_values = {
                    'id': wh.id,
                    'name': wh_location['name'].title(),
                    'street': wh_location['street'].title(),
                    'city': wh_location.city.title(),
                    'zip_code': wh_location.zip,
                    'country_code': wh_location.country_code,
                    'state': wh_location.state_id.code,
                    'latitude': wh_location.partner_latitude,
                    'longitude': wh_location.partner_longitude,
                    'additional_data': {'in_store_stock': in_store_stock_data},
                }
            except AttributeError:
                continue  # Ignore warehouses with badly configured address.

            # Prepare the opening hours data.
            if wh.opening_hours:
                opening_hours_dict = {str(i): [] for i in range(7)}
                for att in wh.opening_hours.attendance_ids:
                    if att.day_period in ('morning', 'afternoon'):
                        opening_hours_dict[att.dayofweek].append(
                            f'{format_duration(att.hour_from)} - {format_duration(att.hour_to)}'
                        )
                pickup_location_values['opening_hours'] = opening_hours_dict
            else:
                pickup_location_values['opening_hours'] = {}

            # Calculate the distance between the partner address and the warehouse location.
            pickup_location_values['distance'] = utils.calculate_partner_distance(
                partner_address, wh_location
            )
            pickup_locations.append(pickup_location_values)

        return sorted(pickup_locations, key=lambda k: k['distance'])

    def in_store_rate_shipment(self, *_args):
        return {
            'success': True,
            'price': self.product_id.list_price,
            'error_message': False,
            'warning_message': False,
        }
