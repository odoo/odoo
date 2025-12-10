# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    seller_id = fields.Many2one(
        'marketplace.seller',
        string='Seller',
        ondelete='restrict',
        tracking=True,
        help='Seller who owns this product',
    )
    external_sku = fields.Char(
        string='External SKU',
        help='External SKU from seller system',
    )
    synced_channels = fields.Text(
        string='Synced Channels',
        default='{}',
        help='JSON format: {"fb": true, "ig": true, "wa": false, "tiktok": false, "ln": false}',
    )
    social_caption_template = fields.Text(
        string='Social Caption Template',
        help='Template for social media posts',
    )
    tiktok_video_url = fields.Char(string='TikTok Video URL')
    availability_status = fields.Selection([
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ], string='Availability Status', compute='_compute_availability_status', store=True)
    shipping_weight_kg = fields.Float(string='Shipping Weight (kg)', default=0.0)
    low_stock_threshold = fields.Integer(string='Low Stock Threshold', default=10, help='Quantity below which product is marked as low stock')
    
    # Marketplace specific fields
    marketplace_published = fields.Boolean(string='Published on Marketplace', default=False)
    marketplace_approved = fields.Boolean(string='Marketplace Approved', default=False)
    
    @api.depends('qty_available', 'type', 'low_stock_threshold')
    def _compute_availability_status(self):
        for product in self:
            if product.type != 'product':
                product.availability_status = 'in_stock'
                continue
            
            qty_available = product.qty_available
            threshold = product.low_stock_threshold or 10
            if qty_available <= 0:
                product.availability_status = 'out_of_stock'
            elif qty_available < threshold:
                product.availability_status = 'low_stock'
            else:
                product.availability_status = 'in_stock'
    
    def get_synced_channels(self):
        """Get synced channels as dict"""
        try:
            return json.loads(self.synced_channels or '{}')
        except:
            return {}
    
    def set_synced_channels(self, channels_dict):
        """Set synced channels from dict"""
        self.synced_channels = json.dumps(channels_dict)
    
    def action_approve_marketplace(self):
        """Approve product for marketplace"""
        self.write({
            'marketplace_approved': True,
            'marketplace_published': True,
        })
    
    def action_reject_marketplace(self):
        """Reject product from marketplace"""
        self.write({
            'marketplace_approved': False,
            'marketplace_published': False,
        })
    
    @api.constrains('seller_id')
    def _check_seller_approved(self):
        for product in self:
            if product.seller_id and product.seller_id.state != 'approved':
                raise ValidationError(_('Product can only be assigned to approved sellers.'))

