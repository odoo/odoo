# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pickup_location_data = fields.Json()
    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method", check_company=True, help="Fill this field if you plan to invoice the shipping based on picking.")
    delivery_message = fields.Char(readonly=True, copy=False)
    delivery_set = fields.Boolean(compute='_compute_delivery_state')
    recompute_delivery_price = fields.Boolean('Delivery cost should be recomputed')
    is_all_service = fields.Boolean("Service Product", compute="_compute_is_service_products")
    shipping_weight = fields.Float("Shipping Weight", compute="_compute_shipping_weight", store=True, readonly=False)

    def _compute_partner_shipping_id(self):
        """ Override to reset the delivery address when a pickup location was selected. """
        super()._compute_partner_shipping_id()
        for order in self:
            if order.partner_shipping_id.is_pickup_location:
                order.partner_shipping_id = order.partner_id

    @api.depends('order_line')
    def _compute_is_service_products(self):
        for so in self:
            so.is_all_service = all(line.product_id.type == 'service' for line in so.order_line.filtered(lambda x: not x.display_type))

    def _compute_amount_total_without_delivery(self):
        self.ensure_one()
        delivery_cost = sum([l.price_total for l in self.order_line if l.is_delivery])
        return self.amount_total - delivery_cost

    @api.depends('order_line')
    def _compute_delivery_state(self):
        for order in self:
            order.delivery_set = any(line.is_delivery for line in order.order_line)

    @api.onchange('order_line', 'partner_id', 'partner_shipping_id')
    def onchange_order_line(self):
        self.ensure_one()
        delivery_line = self.order_line.filtered('is_delivery')
        if delivery_line:
            self.recompute_delivery_price = True

    def _get_update_prices_lines(self):
        """ Exclude delivery lines from price list recomputation based on product instead of carrier """
        lines = super()._get_update_prices_lines()
        return lines.filtered(lambda line: not line.is_delivery)

    def _remove_delivery_line(self):
        """Remove delivery products from the sales orders"""
        delivery_lines = self.order_line.filtered("is_delivery")
        if not delivery_lines:
            return
        to_delete = delivery_lines.filtered(lambda x: x.qty_invoiced == 0)
        if not to_delete:
            raise UserError(
                _('You can not update the shipping costs on an order where it was already invoiced!\n\nThe following delivery lines (product, invoiced quantity and price) have already been processed:\n\n')
                + '\n'.join(['- %s: %s x %s' % (line.product_id.with_context(display_default_code=False).display_name, line.qty_invoiced, line.price_unit) for line in delivery_lines])
            )
        to_delete.unlink()

    def set_delivery_line(self, carrier, amount):
        self._remove_delivery_line()
        for order in self:
            order.carrier_id = carrier.id
            order._create_delivery_line(carrier, amount)
        return True

    def _set_pickup_location(self, pickup_location_data):
        """ Set the pickup location on the current order.

        Note: self.ensure_one()

        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: None
        """
        self.ensure_one()
        use_locations_fname = f'{self.carrier_id.delivery_type}_use_locations'
        if hasattr(self.carrier_id, use_locations_fname):
            use_location = getattr(self.carrier_id, use_locations_fname)
            if use_location and pickup_location_data:
                pickup_location = json.loads(pickup_location_data)
            else:
                pickup_location = None
            self.pickup_location_data = pickup_location

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
            partner_address = self.partner_shipping_id
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

    def action_open_delivery_wizard(self):
        view_id = self.env.ref('delivery.choose_delivery_carrier_view_form').id
        if self.env.context.get('carrier_recompute'):
            name = _('Update shipping cost')
            carrier = self.carrier_id
        else:
            name = _('Add a shipping method')
            shipping_partner_id = self.with_company(self.company_id).partner_shipping_id
            carrier_property = (
                shipping_partner_id.property_delivery_carrier_id
                or shipping_partner_id.commercial_partner_id.property_delivery_carrier_id
            )
            carrier = carrier_property.available_carriers(self.partner_shipping_id, self)
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_carrier_id': carrier.id,
                'default_total_weight': self._get_estimated_weight()
            }
        }

    def _action_confirm(self):
        for order in self:
            order_location = order.pickup_location_data

            if not order_location:
                continue

            # Retrieve all the data : name, street, city, state, zip, country.
            name = order_location.get('name') or order.partner_shipping_id.name
            street = order_location['street']
            city = order_location['city']
            zip_code = order_location['zip_code']
            country_code = order_location['country_code']
            country = order.env['res.country'].search([('code', '=', country_code)]).id
            state = order.env['res.country.state'].search([
                ('code', '=', order_location['state']),
                ('country_id', '=', country),
            ]).id if (order_location.get('state') and country) else None
            parent_id = order.partner_shipping_id.id
            email = order.partner_shipping_id.email
            phone = order.partner_shipping_id.phone

            # Check if the current partner has a partner of type 'delivery' with the same address.
            existing_partner = order.env['res.partner'].search([
                ('street', '=', street),
                ('city', '=', city),
                ('state_id', '=', state),
                ('country_id', '=', country),
                ('parent_id', '=', parent_id),
                ('type', '=', 'delivery'),
            ], limit=1)

            shipping_partner = existing_partner or order.env['res.partner'].create({
                'parent_id': parent_id,
                'type': 'delivery',
                'name': name,
                'street': street,
                'city': city,
                'state_id': state,
                'zip': zip_code,
                'country_id': country,
                'email': email,
                'phone': phone,
                'is_pickup_location': True,
            })
            order.with_context(update_delivery_shipping_partner=True).write({'partner_shipping_id': shipping_partner})
        return super()._action_confirm()

    def _prepare_delivery_line_vals(self, carrier, price_unit):
        context = {}
        if self.partner_id:
            # set delivery detail in the customer language
            context['lang'] = self.partner_id.lang
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id._filter_taxes_by_company(self.company_id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes).ids

        # Create the sales order line

        if carrier.product_id.description_sale:
            so_description = '%s: %s' % (carrier.name,
                                        carrier.product_id.description_sale)
        else:
            so_description = carrier.name
        values = {
            'order_id': self.id,
            'name': so_description,
            'price_unit': price_unit,
            'product_uom_qty': 1,
            'product_id': carrier.product_id.id,
            'tax_ids': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        if carrier.free_over and self.currency_id.is_zero(price_unit) :
            values['name'] = _('%s\nFree Shipping', values['name'])
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        del context
        return values

    def _create_delivery_line(self, carrier, price_unit):
        values = self._prepare_delivery_line_vals(carrier, price_unit)
        return self.env['sale.order.line'].sudo().create(values)

    @api.depends('order_line.product_uom_qty', 'order_line.product_uom_id')
    def _compute_shipping_weight(self):
        for order in self:
            order.shipping_weight = order._get_estimated_weight()

    def _get_estimated_weight(self):
        self.ensure_one()
        weight = 0.0
        for order_line in self.order_line.filtered(lambda l: l.product_id.type == 'consu' and not l.is_delivery and not l.display_type and l.product_uom_qty > 0):
            weight += order_line.product_qty * order_line.product_id.weight
        return weight

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """ Override of `sale` to recompute the delivery prices.

        :param int product_id: The product, as a `product.product` id.
        :return: The unit price price of the product, based on the pricelist of the sale order and
                 the quantity selected.
        :rtype: float
        """
        price_unit = super()._update_order_line_info(product_id, quantity, **kwargs)
        if self:
            self.onchange_order_line()
        return price_unit
