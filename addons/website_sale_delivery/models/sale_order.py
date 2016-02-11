# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.mixin']

    website_description = fields.Text(related='product_id.description_sale', string='Description for Online Quotations')
    website_published = fields.Boolean(default=False)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_delivery = fields.Monetary(
        compute='_compute_amount_delivery', digits=0,
        string='Delivery Amount',
        help="The amount without tax.", store=True, track_visibility='always')
    has_delivery = fields.Boolean(
        compute='_compute_has_delivery', string='Has delivery',
        help="Has an order line set for delivery", store=True)
    website_order_line = fields.One2many(
        'sale.order.line', 'order_id',
        string='Order Lines displayed on Website', readonly=True,
        domain=[('is_delivery', '=', False)],
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.')

    @api.depends('order_line.price_unit', 'order_line.tax_id', 'order_line.discount', 'order_line.product_uom_qty')
    def _compute_amount_delivery(self):
        for order in self:
            order.amount_delivery = sum(order.order_line.filtered('is_delivery').mapped('price_subtotal'))

    @api.depends('order_line.is_delivery')
    def _compute_has_delivery(self):
        for order in self:
            order.has_delivery = any(order.order_line.filtered('is_delivery'))

    def _check_carrier_quotation(self, force_carrier_id=None):
        # check to add or remove carrier_id
        if not self:
            return False
        self.ensure_one()
        if self.only_services:
            self.write({'carrier_id': None})
            self._delivery_unset()
            return True
        else:
            carrier_id = force_carrier_id or self.carrier_id.id
            carrier_ids = self._get_delivery_methods()
            if carrier_id:
                if carrier_id not in carrier_ids:
                    carrier_id = False
                else:
                    carrier_ids.remove(carrier_id)
                    carrier_ids.insert(0, carrier_id)
            if force_carrier_id or not carrier_id or carrier_id not in carrier_ids:
                for delivery in self.env['delivery.carrier'].sudo().browse(carrier_ids):
                    carrier = delivery.verify_carrier(self.partner_shipping_id)
                    if carrier:
                        carrier_id = delivery.id
                        break
                self.write({'carrier_id': carrier_id})
            if carrier_id:
                self.delivery_set()
            else:
                self._delivery_unset()

        return bool(carrier_id)

    def _get_delivery_methods(self):
        self.ensure_one()
        available_carrier_ids = []
        # Following loop is done to avoid displaying delivery methods who are not available for this order
        # This can surely be done in a more efficient way, but at the moment, it mimics the way it's
        # done in delivery_set method of sale.py, from delivery module
        carriers = self.env['delivery.carrier'].with_context(order_id=self.id).sudo().search(
            [('website_published', '=', True)])
        for carrier in carriers:
            try:
                _logger.debug("Checking availability of carrier #%s" % carrier.id)
                available = carrier.read(fields=['available'])[0]['available']
                if available:
                    available_carrier_ids.append(carrier.id)
            except ValidationError as e:
                # RIM TODO: hack to remove, make available field not depend on a SOAP call to external shipping provider
                # The validation error is used in backend to display errors in fedex config, but should fail silently in frontend
                _logger.debug("Carrier #%s removed from e-commerce carrier list. %s" % (carrier.id, e))
        return available_carrier_ids

    @api.model
    def _get_errors(self, order):
        errors = super(SaleOrder, self)._get_errors(order)
        if not order._get_delivery_methods():
            errors.append(
                (_('Sorry, we are unable to ship your order'),
                 _('No shipping method is available for your current order and shipping address. '
                   'Please contact us for more information.')))
        return errors

    @api.model
    def _get_website_data(self, order):
        """ Override to add delivery-related website data. """
        values = super(SaleOrder, self)._get_website_data(order)
        # We need a delivery only if we have stockable products
        has_stockable_products = any(order.order_line.filtered(lambda line: line.product_id.type in ['consu', 'product']))
        if not has_stockable_products:
            return values

        delivery_ids = order._get_delivery_methods()

        values['deliveries'] = self.env['delivery.carrier'].sudo().with_context(order_id=order.id).browse(delivery_ids)
        return values

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Override to update carrier quotation if quantity changed """

        values = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)

        if add_qty or set_qty is not None:
            for sale_order in self:
                self._check_carrier_quotation()

        return values

    def _get_shipping_country(self, values):
        countries = self.env['res.country']
        states = self.env['res.country.state']
        values['shipping_countries'] = values['countries']
        values['shipping_states'] = values['states']

        delivery_carriers = self.env['delivery.carrier'].sudo().search([('website_published', '=', True)])
        for carrier in delivery_carriers:
            if not carrier.country_ids and not carrier.state_ids:
                return values
            # Authorized shipping countries
            countries |= carrier.country_ids
            # Authorized shipping countries without any state restriction
            state_countries = carrier.country_ids - carrier.state_ids.mapped('country_id')
            # Authorized shipping states + all states from shipping countries without any state restriction
            states |= carrier.state_ids | values['states'].filtered(lambda state: state.country_id in state_countries)

        values['shipping_countries'] = values['countries'] & countries
        values['shipping_states'] = values['states'] & states
        return values
