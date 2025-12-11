# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    marketplace_order = fields.Boolean(string='Marketplace Order', default=False, index=True)
    seller_id = fields.Many2one(
        'marketplace.seller',
        string='Seller',
        ondelete='restrict',
        tracking=True,
        help='Seller for this order (for single-seller orders)',
    )
    social_source = fields.Char(
        string='Social Source',
        help='Source of order: facebook_shop, instagram_checkout, etc.',
    )
    parent_order_id = fields.Many2one(
        'sale.order',
        string='Parent Order',
        help='Parent order for multi-seller split orders',
    )
    child_order_ids = fields.One2many(
        'sale.order',
        'parent_order_id',
        string='Child Orders',
        help='Child orders for multi-seller split',
    )
    delivery_tracking_ids = fields.One2many(
        'marketplace.delivery.tracking',
        'order_id',
        string='Delivery Tracking',
    )
    
    # Commission fields
    commission_amount = fields.Monetary(
        string='Commission Amount',
        compute='_compute_commission',
        store=True,
    )
    seller_amount = fields.Monetary(
        string='Seller Amount',
        compute='_compute_commission',
        store=True,
    )
    
    @api.depends('order_line', 'seller_id', 'amount_total')
    def _compute_commission(self):
        for order in self:
            if order.marketplace_order and order.seller_id:
                commission_type = order.seller_id.commission_type
                commission_value = order.seller_id.commission_value
                
                if commission_type == 'percentage':
                    order.commission_amount = order.amount_total * (commission_value / 100.0)
                else:
                    order.commission_amount = commission_value
                
                order.seller_amount = order.amount_total - order.commission_amount
            else:
                order.commission_amount = 0.0
                order.seller_amount = order.amount_total
    
    def action_split_by_seller(self):
        """Split order by seller for multi-seller checkout"""
        if not self.marketplace_order:
            raise UserError(_('This is not a marketplace order.'))
        
        # Group order lines by seller
        seller_lines = {}
        for line in self.order_line:
            seller = line.product_id.seller_id or self.seller_id
            if seller:
                if seller.id not in seller_lines:
                    seller_lines[seller.id] = []
                seller_lines[seller.id].append(line)
        
        if len(seller_lines) <= 1:
            raise UserError(_('Order contains products from only one seller. No split needed.'))
        
        # Create child orders
        child_orders = self.env['sale.order']
        for seller_id, lines in seller_lines.items():
            seller = self.env['marketplace.seller'].browse(seller_id)
            child_order = self.copy({
                'parent_order_id': self.id,
                'seller_id': seller.id,
                'order_line': [(6, 0, lines.ids)],
            })
            child_orders |= child_order
        
        # Remove lines from parent order
        self.write({
            'order_line': [(5, 0, 0)],
            'child_order_ids': [(6, 0, child_orders.ids)],
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Split Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', child_orders.ids)],
            'target': 'current',
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    seller_id = fields.Many2one(
        'marketplace.seller',
        string='Seller',
        related='product_id.seller_id',
        store=True,
        readonly=True,
    )


class MarketplaceDeliveryTracking(models.Model):
    _name = 'marketplace.delivery.tracking'
    _description = 'Delivery Tracking'
    _order = 'create_date desc'

    name = fields.Char(string='Tracking Number', required=True)
    order_id = fields.Many2one('sale.order', string='Order', required=True, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', string='Picking')
    carrier_id = fields.Many2one('delivery.carrier', string='Carrier')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ], string='Status', default='pending', required=True)
    tracking_url = fields.Char(string='Tracking URL')
    notes = fields.Text(string='Notes')

