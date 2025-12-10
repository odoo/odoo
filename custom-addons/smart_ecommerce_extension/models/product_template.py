# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import timedelta


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Brand and Model fields
    brand = fields.Char(
        string='Brand',
        index=True,
        tracking=True,
        help='Product brand name for filtering and display',
    )
    product_model = fields.Char(
        string='Model',
        tracking=True,
        help='Product model number or name',
    )
    
    # Rich specifications
    specifications = fields.Html(
        string='Specifications',
        sanitize_attributes=False,
        help='Detailed product specifications in HTML format',
    )
    
    # Video support
    video_url = fields.Char(
        string='Video URL',
        help='YouTube, Vimeo, or direct video URL for product demonstration',
    )
    
    # Second image for hover effect
    image_hover = fields.Binary(
        string='Hover Image',
        attachment=True,
        help='Secondary image shown on product card hover',
    )
    
    # Availability - Extend if not already present (check marketplace_core)
    availability_status = fields.Selection([
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ], string='Availability Status', compute='_compute_availability_status', store=True)
    
    low_stock_threshold = fields.Integer(
        string='Low Stock Threshold',
        default=10,
        help='Quantity below which product is marked as low stock',
    )
    
    # Delivery estimation
    estimated_delivery_days = fields.Integer(
        string='Estimated Delivery Days',
        default=3,
        help='Default number of days for delivery estimation',
    )
    
    # Shipping weight (if not from marketplace_core)
    shipping_weight_kg = fields.Float(
        string='Shipping Weight (kg)',
        default=0.0,
        help='Product weight in kilograms for shipping calculations',
    )

    @api.depends('qty_available', 'type', 'low_stock_threshold')
    def _compute_availability_status(self):
        """Compute availability status based on stock quantity"""
        for product in self:
            if product.type != 'product':
                product.availability_status = 'in_stock'
                continue
            
            qty = product.qty_available
            threshold = product.low_stock_threshold or 10
            
            if qty <= 0:
                product.availability_status = 'out_of_stock'
            elif qty < threshold:
                product.availability_status = 'low_stock'
            else:
                product.availability_status = 'in_stock'

    def get_availability_badge_class(self):
        """Return CSS class for availability badge"""
        self.ensure_one()
        mapping = {
            'in_stock': 'badge-success',
            'low_stock': 'badge-warning',
            'out_of_stock': 'badge-danger',
        }
        return mapping.get(self.availability_status, 'badge-secondary')

    def get_availability_label(self):
        """Return human-readable availability label"""
        self.ensure_one()
        labels = {
            'in_stock': _('In Stock'),
            'low_stock': _('Low Stock'),
            'out_of_stock': _('Out of Stock'),
        }
        return labels.get(self.availability_status, _('Unknown'))

    def get_estimated_delivery_date(self, city=None):
        """
        Calculate estimated delivery date based on product and delivery zone.
        
        Args:
            city: Customer city for zone-based estimation
            
        Returns:
            dict with min_date, max_date, and formatted string
        """
        self.ensure_one()
        base_days = self.estimated_delivery_days or 3
        
        # Check for delivery zone override
        if city:
            zone = self.env['delivery.zone'].search([
                ('city_ids', 'ilike', city)
            ], limit=1)
            if zone and zone.estimated_days:
                base_days = zone.estimated_days
        
        # Calculate dates (skip weekends for business days)
        today = fields.Date.today()
        min_date = today + timedelta(days=base_days)
        max_date = today + timedelta(days=base_days + 2)
        
        return {
            'min_date': min_date,
            'max_date': max_date,
            'formatted': _('%(min)s - %(max)s') % {
                'min': min_date.strftime('%b %d'),
                'max': max_date.strftime('%b %d'),
            },
            'days_range': f"{base_days}-{base_days + 2}",
        }

    def get_video_embed_url(self):
        """Convert video URL to embeddable format"""
        self.ensure_one()
        if not self.video_url:
            return False
        
        url = self.video_url.strip()
        
        # YouTube
        if 'youtube.com/watch' in url:
            video_id = url.split('v=')[1].split('&')[0] if 'v=' in url else None
            if video_id:
                return f'https://www.youtube.com/embed/{video_id}'
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        
        # Vimeo
        if 'vimeo.com/' in url:
            video_id = url.split('vimeo.com/')[1].split('?')[0]
            return f'https://player.vimeo.com/video/{video_id}'
        
        return url  # Return as-is for direct URLs

    @api.model
    def get_brands(self, limit=50):
        """Get list of unique brands for filtering"""
        self.env.cr.execute("""
            SELECT DISTINCT brand
            FROM product_template
            WHERE brand IS NOT NULL 
              AND brand != ''
              AND is_published = true
            ORDER BY brand
            LIMIT %s
        """, (limit,))
        return [row[0] for row in self.env.cr.fetchall()]

