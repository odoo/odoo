# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


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
            if self.env.user.has_group('sale.group_show_price_subtotal'):
                order.amount_delivery = sum(order.order_line.filtered('is_delivery').mapped('price_subtotal'))
            else:
                order.amount_delivery = sum(order.order_line.filtered('is_delivery').mapped('price_total'))

    @api.depends('order_line.is_delivery')
    def _compute_has_delivery(self):
        for order in self:
            order.has_delivery = any(order.order_line.filtered('is_delivery'))

    def _check_carrier_quotation(self, force_carrier_id=None):
        # check to add or remove carrier_id
        if not self:
            return False
        self.ensure_one()
        DeliveryCarrier = self.env['delivery.carrier']
        if self.only_services:
            self.write({'carrier_id': None})
            self._delivery_unset()
            return True
        else:
            carrier = force_carrier_id and DeliveryCarrier.browse(force_carrier_id) or self.carrier_id
            available_carriers = self._get_delivery_methods()
            if carrier:
                if carrier not in available_carriers:
                    carrier = DeliveryCarrier
                else:
                    # set the forced carrier at the beginning of the list to be verfied first below
                    available_carriers -= carrier
                    available_carriers = carrier + available_carriers
            if force_carrier_id or not carrier or carrier not in available_carriers:
                for delivery in available_carriers:
                    verified_carrier = delivery.verify_carrier(self.partner_shipping_id)
                    if verified_carrier:
                        carrier = delivery
                        break
                self.write({'carrier_id': carrier.id})
            if carrier:
                self.delivery_set()
            else:
                self._delivery_unset()

        return bool(carrier)

    def _get_delivery_methods(self):
        """Return the available and published delivery carriers"""
        self.ensure_one()
        available_carriers = DeliveryCarrier = self.env['delivery.carrier']
        # Following loop is done to avoid displaying delivery methods who are not available for this order
        # This can surely be done in a more efficient way, but at the moment, it mimics the way it's
        # done in delivery_set method of sale.py, from delivery module
        carrier_ids = DeliveryCarrier.sudo().search(
            [('website_published', '=', True)]).ids
        for carrier_id in carrier_ids:
            carrier = DeliveryCarrier.browse(carrier_id)
            try:
                _logger.debug("Checking availability of carrier #%s" % carrier_id)
                available = carrier.with_context(order_id=self.id).read(fields=['available'])[0]['available']
                if available:
                    available_carriers += carrier
            except ValidationError as e:
                # RIM TODO: hack to remove, make available field not depend on a SOAP call to external shipping provider
                # The validation error is used in backend to display errors in fedex config, but should fail silently in frontend
                _logger.debug("Carrier #%s removed from e-commerce carrier list. %s" % (carrier_id, e))
        return available_carriers

    @api.model
    def _get_errors(self, order):
        # Do not Forward port in v11.0 as the API was refactored by f9a8c53e485445bc8e3474eb3978b0f83d5645c7
        has_stockable_products = any(order.order_line.filtered(lambda line: line.product_id.type in ['consu', 'product']))
        errors = super(SaleOrder, self)._get_errors(order)
        if not order._get_delivery_methods() and has_stockable_products:
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

        delivery_carriers = order._get_delivery_methods()
        values['deliveries'] = delivery_carriers.sudo().with_context(order_id=order.id)
        return values

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Override to update carrier quotation if quantity changed """

        self._delivery_unset()

        # When you update a cart, it is not enouf to remove the "delivery cost" line
        # The carrier might also be invalid, eg: if you bought things that are too heavy
        # -> this may cause a bug if you go to the checkout screen, choose a carrier,
        #    then update your cart (the cart becomes uneditable)
        self.write({'carrier_id': False})

        values = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)

        if add_qty or set_qty is not None:
            for sale_order in self:
                self._check_carrier_quotation()

        return values
