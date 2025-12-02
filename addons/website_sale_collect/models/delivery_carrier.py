# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.http import request

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
                vals['allow_cash_on_delivery'] = False

                # Set the default warehouses and publish if one is found.
                if 'company_id' in vals:
                    company_id = vals.get('company_id')
                else:
                    company_id = (
                        self.env['product.product'].browse(vals.get('product_id')).company_id.id
                        or self.env.company.id
                    )
                warehouses = self.env['stock.warehouse'].search(
                    [('company_id', 'in', company_id)]
                )
                vals.update({
                    'warehouse_ids': [Command.set(warehouses.ids)],
                    'is_published': bool(warehouses),
                })
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('delivery_type') == 'in_store':
            vals['integration_level'] = 'rate'
            vals['allow_cash_on_delivery'] = False
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
        order_sudo = request.cart
        for wh in self.warehouse_ids:
            pickup_location_values = wh._prepare_pickup_location_data()
            if not pickup_location_values:  # Ignore warehouses with badly configured addresses.
                continue

            # Prepare the stock data based on either the product or the order.
            if product:  # Called from the product page.
                in_store_stock_data = utils.format_product_stock_values(product, wh.id)
            else:  # Called from the checkout page.
                in_store_stock_data = {'in_stock': order_sudo._is_in_stock(wh.id)}

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
