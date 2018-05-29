# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

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
        self.ensure_one()
        DeliveryCarrier = self.env['delivery.carrier']

        if self.only_services:
            self.write({'carrier_id': None})
            self._remove_delivery_line()
            return True
        else:
            # attempt to use partner's preferred carrier
            if not force_carrier_id and self.partner_shipping_id.property_delivery_carrier_id:
                force_carrier_id = self.partner_shipping_id.property_delivery_carrier_id.id

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
                    verified_carrier = delivery._match_address(self.partner_shipping_id)
                    if verified_carrier:
                        carrier = delivery
                        break
                self.write({'carrier_id': carrier.id})
            self._remove_delivery_line()
            if carrier:
                self.get_delivery_price()
                if self.delivery_rating_success:
                    self.set_delivery_line()

        return bool(carrier)

    def _get_delivery_methods(self):
        address = self.partner_shipping_id
        return self.env['delivery.carrier'].sudo().search([('website_published', '=', True)]).available_carriers(address)

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Override to update carrier quotation if quantity changed """

        self._remove_delivery_line()

        # When you update a cart, it is not enouf to remove the "delivery cost" line
        # The carrier might also be invalid, eg: if you bought things that are too heavy
        # -> this may cause a bug if you go to the checkout screen, choose a carrier,
        #    then update your cart (the cart becomes uneditable)
        self.write({'carrier_id': False})

        values = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)

        return values
