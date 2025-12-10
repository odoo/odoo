# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)


class SocialPostQueue(models.Model):
    _name = 'social.post.queue'
    _description = 'Social Media Post Queue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_at asc, create_date asc'

    name = fields.Char(string='Post Name', compute='_compute_name', store=True)
    product_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade')
    seller_id = fields.Many2one('marketplace.seller', related='product_id.seller_id', store=True, readonly=True)
    
    channel = fields.Selection([
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('tiktok', 'TikTok'),
        ('linkedin', 'LinkedIn'),
    ], string='Channel', required=True)
    
    status = fields.Selection([
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('posted', 'Posted'),
        ('failed', 'Failed'),
    ], string='Status', default='pending', required=True, tracking=True)
    
    scheduled_at = fields.Datetime(string='Scheduled At', required=True, default=fields.Datetime.now)
    posted_at = fields.Datetime(string='Posted At', readonly=True)
    
    payload = fields.Text(string='Payload', help='JSON payload for the post')
    external_post_id = fields.Char(string='External Post ID', readonly=True)
    
    attempts = fields.Integer(string='Attempts', default=0, readonly=True)
    max_attempts = fields.Integer(string='Max Attempts', default=3)
    error_message = fields.Text(string='Error Message', readonly=True)
    
    # Media
    image_url = fields.Char(string='Image URL')
    video_url = fields.Char(string='Video URL')
    caption = fields.Text(string='Caption')
    
    @api.depends('product_id', 'channel', 'scheduled_at')
    def _compute_name(self):
        for post in self:
            post.name = f"{post.product_id.name or 'Product'} - {post.channel.upper()} - {post.scheduled_at.strftime('%Y-%m-%d %H:%M') if post.scheduled_at else ''}"
    
    def action_post_now(self):
        """Post immediately"""
        for post in self:
            if post.status == 'posted':
                raise UserError(_('Post already published.'))
            post._post_to_social()
    
    def _post_to_social(self):
        """Post to social media channel"""
        for post in self:
            try:
                # Get connector service (placeholder - requires smart_social_connector module)
                # connector = self.env['social.connector.service'].get_connector(post.channel)
                # if not connector:
                #     raise UserError(_('Social connector not configured for %s') % post.channel)
                
                # Placeholder implementation - actual connector will be in smart_social_connector module
                _logger.warning(f"Social connector not yet implemented for {post.channel}. Install smart_social_connector module.")
                raise UserError(_('Social connector module (smart_social_connector) not installed. Please install it to post to social media.'))
                
                # Prepare post data
                post_data = self._prepare_post_data()
                
                # Post to social media
                result = connector.post(post_data)
                
                if result.get('success'):
                    post.write({
                        'status': 'posted',
                        'posted_at': fields.Datetime.now(),
                        'external_post_id': result.get('post_id'),
                        'error_message': False,
                    })
                else:
                    post.write({
                        'status': 'failed',
                        'attempts': post.attempts + 1,
                        'error_message': result.get('error', 'Unknown error'),
                    })
            except Exception as e:
                _logger.error(f"Error posting to {post.channel}: {str(e)}")
                post.write({
                    'status': 'failed',
                    'attempts': post.attempts + 1,
                    'error_message': str(e),
                })
    
    def _prepare_post_data(self):
        """Prepare post data for social media"""
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'product_name': self.product_id.name,
            'product_url': f"/shop/product/{self.product_id.id}",
            'image_url': self.image_url or (self.product_id.image_128 and f"/web/image/product.template/{self.product_id.id}/image_128"),
            'caption': self.caption or self.product_id.social_caption_template or self.product_id.description_sale or '',
            'seller_name': self.seller_id.name if self.seller_id else '',
        }
    
    @api.model
    def cron_process_queue(self):
        """Cron job to process scheduled posts"""
        now = fields.Datetime.now()
        posts = self.search([
            ('status', 'in', ['pending', 'scheduled']),
            ('scheduled_at', '<=', now),
        ]).filtered(lambda p: p.attempts < p.max_attempts)
        
        for post in posts:
            try:
                post._post_to_social()
            except Exception as e:
                _logger.error(f"Error processing post {post.id}: {str(e)}")
    
    def get_payload(self):
        """Get payload as dict"""
        try:
            return json.loads(self.payload or '{}')
        except:
            return {}
    
    def set_payload(self, data):
        """Set payload from dict"""
        self.payload = json.dumps(data)

