# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Delivery zone
    delivery_zone_id = fields.Many2one(
        'delivery.zone',
        string='Delivery Zone',
        compute='_compute_delivery_zone',
        store=True,
        readonly=False,
    )
    
    # Computed delivery info
    computed_delivery_price = fields.Monetary(
        string='Computed Delivery Price',
        compute='_compute_delivery_info',
        store=True,
        currency_field='currency_id',
    )
    estimated_delivery_date = fields.Date(
        string='Estimated Delivery Date',
        compute='_compute_delivery_info',
        store=True,
    )
    total_shipping_weight = fields.Float(
        string='Total Shipping Weight',
        compute='_compute_total_weight',
        store=True,
        help='Total weight of all products in kg',
    )

    @api.depends('partner_shipping_id', 'partner_shipping_id.city')
    def _compute_delivery_zone(self):
        """Auto-detect delivery zone based on shipping address city"""
        DeliveryZone = self.env['delivery.zone']
        for order in self:
            city = order.partner_shipping_id.city if order.partner_shipping_id else None
            zone = DeliveryZone.find_zone_for_city(city)
            order.delivery_zone_id = zone.id if zone else False

    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_total_weight(self):
        """Compute total shipping weight from order lines"""
        for order in self:
            total = 0.0
            for line in order.order_line:
                if line.product_id and line.product_id.type == 'product':
                    weight = line.product_id.shipping_weight_kg or line.product_id.weight or 0.0
                    total += weight * line.product_uom_qty
            order.total_shipping_weight = total

    @api.depends('delivery_zone_id', 'total_shipping_weight', 'amount_untaxed')
    def _compute_delivery_info(self):
        """Compute delivery price and estimated date based on zone"""
        for order in self:
            if order.delivery_zone_id:
                zone = order.delivery_zone_id
                try:
                    order.computed_delivery_price = zone.compute_delivery_price(
                        order.total_shipping_weight or 1.0,
                        order.amount_untaxed,
                    )
                except Exception:
                    order.computed_delivery_price = zone.base_price
                
                order.estimated_delivery_date = fields.Date.today() + timedelta(
                    days=zone.estimated_days
                )
            else:
                order.computed_delivery_price = 0.0
                order.estimated_delivery_date = fields.Date.today() + timedelta(days=5)

    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id', 'computed_delivery_price')
    def _compute_amounts(self):
        """Include computed delivery price in order totals"""
        super()._compute_amounts()
        for order in self:
            delivery_price = order.computed_delivery_price or 0.0
            order.amount_untaxed += delivery_price
            order.amount_total += delivery_price

    def get_delivery_info(self):
        """Get delivery information for API/template use"""
        self.ensure_one()
        zone = self.delivery_zone_id
        
        return {
            'zone': {
                'id': zone.id if zone else None,
                'name': zone.name if zone else _('Standard Delivery'),
            },
            'price': self.computed_delivery_price,
            'weight_kg': self.total_shipping_weight,
            'estimated_date': self.estimated_delivery_date.isoformat() if self.estimated_delivery_date else None,
            'delivery_range': zone.get_delivery_estimate() if zone else _('5-7 days'),
            'free_threshold': zone.free_delivery_threshold if zone else 0.0,
            'is_free': self.computed_delivery_price == 0.0,
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    shipping_weight = fields.Float(
        string='Shipping Weight',
        compute='_compute_shipping_weight',
        help='Product shipping weight * quantity',
    )

    @api.depends('product_id', 'product_uom_qty')
    def _compute_shipping_weight(self):
        for line in self:
            if line.product_id and line.product_id.type == 'product':
                weight = line.product_id.shipping_weight_kg or line.product_id.weight or 0.0
                line.shipping_weight = weight * line.product_uom_qty
            else:
                line.shipping_weight = 0.0

