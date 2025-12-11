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
            # Only auto-detect if zone is not manually set
            if not order.delivery_zone_id:
                city = order.partner_shipping_id.city if order.partner_shipping_id else None
                if city:
                    zone = DeliveryZone.find_zone_for_city(city)
                    if zone:
                        order.delivery_zone_id = zone.id

    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_total_weight(self):
        """Compute total shipping weight from order lines"""
        for order in self:
            total = 0.0
            for line in order.order_line:
                if line.product_id and line.product_id.is_storable:
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
        """Compute order amounts - delivery line will be included automatically if it exists"""
        # First compute base amounts - this will include delivery lines if they exist
        super()._compute_amounts()
        
        # For website orders with zone but no delivery line yet, add delivery to total
        # This ensures the website shows the correct total before the line is created
        for order in self:
            if order.website_id and order.delivery_zone_id and not order.carrier_id:
                delivery_lines = order.order_line.filtered('is_delivery')
                if not delivery_lines:
                    # No delivery line yet, add computed price to total for display
                    delivery_price = order.computed_delivery_price or 0.0
                    order.amount_total += delivery_price

    @api.depends('order_line.price_total', 'order_line.price_subtotal', 'computed_delivery_price', 'delivery_zone_id', 'website_id')
    def _compute_amount_delivery(self):
        """Override to include zone-based delivery price when no carrier is set"""
        # First compute standard delivery from delivery lines
        super()._compute_amount_delivery()
        
        for order in self.filtered('website_id'):
            # If we have a zone-based delivery price and no carrier delivery lines,
            # use the zone-based price
            if order.delivery_zone_id and order.computed_delivery_price:
                delivery_lines = order.order_line.filtered('is_delivery')
                if not delivery_lines:
                    # No standard delivery lines, use zone-based price
                    if order.website_id.show_line_subtotals_tax_selection == 'tax_excluded':
                        # For tax excluded, use the computed price as-is (assuming no tax on delivery)
                        order.amount_delivery = order.computed_delivery_price
                    else:
                        # For tax included, use the computed price as-is
                        order.amount_delivery = order.computed_delivery_price

    def _update_address(self, partner_id, fnames=None):
        """Override to auto-detect delivery zone when shipping address changes"""
        # Call parent method first
        super()._update_address(partner_id, fnames)
        
        # Auto-detect delivery zone when shipping address is updated
        if fnames and 'partner_shipping_id' in fnames and self.partner_shipping_id:
            partner = self.partner_shipping_id
            if partner.city and not self.delivery_zone_id:
                # Only auto-detect if no zone is currently selected
                DeliveryZone = self.env['delivery.zone']
                zone = DeliveryZone.find_zone_for_city(partner.city)
                if zone:
                    self.delivery_zone_id = zone.id
                    # Trigger recomputation
                    self._compute_delivery_info()
                    self._compute_amount_delivery()
                    self._compute_amounts()

    def _get_delivery_product(self):
        """Get or create a delivery product for zone-based delivery"""
        self.ensure_one()
        # Search for existing delivery product
        delivery_product = self.env['product.product'].search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True),
            ('name', 'ilike', 'Delivery Service'),
        ], limit=1)
        
        if not delivery_product:
            # Create a delivery product if it doesn't exist
            delivery_product = self.env['product.product'].create({
                'name': _('Delivery Service'),
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'invoice_policy': 'order',
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            })
        
        return delivery_product

    def _ensure_zone_delivery_line(self):
        """Ensure delivery line exists for zone-based delivery (called before invoice creation)"""
        for order in self:
            if not order.website_id or not order.delivery_zone_id or order.carrier_id:
                continue
            
            delivery_price = order.computed_delivery_price or 0.0
            if delivery_price <= 0.0:
                continue
            
            # Get delivery product
            delivery_product = order._get_delivery_product()
            
            # Check if delivery line already exists
            existing_line = order.order_line.filtered(
                lambda l: l.is_delivery and l.product_id == delivery_product
            )
            
            if existing_line:
                # Update existing line if price changed
                if abs(existing_line.price_unit - delivery_price) > 0.01:
                    zone_name = order.delivery_zone_id.name
                    existing_line.write({
                        'name': _('Delivery: %s') % zone_name,
                        'price_unit': delivery_price,
                    })
                continue
            
            # Create delivery line
            zone_name = order.delivery_zone_id.name
            line_name = _('Delivery: %s') % zone_name
            
            # Apply fiscal position for taxes
            taxes = delivery_product.taxes_id._filter_taxes_by_company(order.company_id)
            taxes_ids = taxes.ids
            if order.partner_id and order.fiscal_position_id:
                taxes_ids = order.fiscal_position_id.map_tax(taxes).ids
            
            line_vals = {
                'order_id': order.id,
                'name': line_name,
                'price_unit': delivery_price,
                'product_uom_qty': 1,
                'product_uom': delivery_product.uom_id.id,
                'product_id': delivery_product.id,
                'tax_id': [(6, 0, taxes_ids)],
                'is_delivery': True,
            }
            
            if order.order_line:
                line_vals['sequence'] = max(order.order_line.mapped('sequence')) + 1
            else:
                line_vals['sequence'] = 10
            
            self.env['sale.order.line'].create(line_vals)

    def _prepare_invoice(self):
        """Override to ensure delivery line exists before invoice creation"""
        # Ensure delivery line is created before preparing invoice
        self._ensure_zone_delivery_line()
        return super()._prepare_invoice()

    def action_confirm(self):
        """Override to ensure delivery line exists before confirmation"""
        # Ensure delivery line is created before confirming
        self._ensure_zone_delivery_line()
        return super().action_confirm()

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
            if line.product_id and line.product_id.is_storable:
                weight = line.product_id.shipping_weight_kg or line.product_id.weight or 0.0
                line.shipping_weight = weight * line.product_uom_qty
            else:
                line.shipping_weight = 0.0

