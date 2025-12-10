# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json


class MarketplaceSeller(models.Model):
    _name = 'marketplace.seller'
    _description = 'Marketplace Seller'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Seller Name', required=True, related='partner_id.name', store=True, readonly=False)
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # KYC Documents
    kyc_documents = fields.One2many(
        'marketplace.seller.document',
        'seller_id',
        string='KYC Documents',
    )
    kyc_complete = fields.Boolean(string='KYC Complete', compute='_compute_kyc_complete', store=True)
    
    # Commission Configuration
    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Commission Type', default='percentage', required=True)
    commission_value = fields.Float(string='Commission Value', required=True, default=10.0)
    
    # Payout Configuration
    payout_account_details = fields.Text(
        string='Payout Account Details',
        help='JSON format: bank account, IBAN, etc.',
    )
    
    # Social Channels
    social_channels = fields.Text(
        string='Social Channels',
        default='{}',
        help='JSON format: {"facebook": true, "instagram": true, "whatsapp": false, "tiktok": false, "linkedin": false}',
    )
    
    # Ratings
    rating = fields.Float(string='Rating', compute='_compute_rating', store=True)
    rating_count = fields.Integer(string='Rating Count', compute='_compute_rating', store=True)
    
    # Additional Fields
    active = fields.Boolean(string='Active', default=True)
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(string='Updated At', default=fields.Datetime.now, readonly=True, compute='_compute_updated_at', store=True)
    
    # Relations - One2many fields linking to extended models
    product_ids = fields.One2many('product.template', 'seller_id', string='Products')
    order_ids = fields.One2many('sale.order', 'seller_id', string='Orders')
    # Note: payout_batch_ids is added by smart_marketplace_payout module
    
    # Computed Fields
    total_sales = fields.Monetary(string='Total Sales', compute='_compute_sales_stats', store=True)
    total_orders = fields.Integer(string='Total Orders', compute='_compute_sales_stats', store=True)
    total_products = fields.Integer(string='Total Products', compute='_compute_total_products')
    currency_id = fields.Many2one('res.currency', related='partner_id.currency_id', store=True)
    
    def _compute_total_products(self):
        for seller in self:
            seller.total_products = len(seller.product_ids.filtered(lambda p: p.marketplace_published))
    
    def action_view_products(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products'),
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('seller_id', '=', self.id)],
        }
    
    def action_view_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('seller_id', '=', self.id)],
        }
    
    @api.depends('kyc_documents', 'kyc_documents.state')
    def _compute_kyc_complete(self):
        for seller in self:
            required_docs = self.env['marketplace.seller.document.type'].search([('required', '=', True)])
            uploaded_docs = seller.kyc_documents.filtered(lambda d: d.state == 'approved')
            seller.kyc_complete = len(required_docs) > 0 and all(
                doc_type.id in uploaded_docs.mapped('document_type_id').ids
                for doc_type in required_docs
            )
    
    @api.depends('order_ids', 'order_ids.state', 'order_ids.amount_total')
    def _compute_sales_stats(self):
        for seller in self:
            confirmed_orders = seller.order_ids.filtered(lambda o: o.state in ('sale', 'done'))
            seller.total_sales = sum(confirmed_orders.mapped('amount_total'))
            seller.total_orders = len(confirmed_orders)
    
    @api.depends('partner_id.rating_ids')
    def _compute_rating(self):
        for seller in self:
            ratings = self.env['rating.rating'].search([
                ('res_model', '=', 'marketplace.seller'),
                ('res_id', '=', seller.id),
            ])
            if ratings:
                seller.rating = sum(ratings.mapped('rating')) / len(ratings)
                seller.rating_count = len(ratings)
            else:
                seller.rating = 0.0
                seller.rating_count = 0
    
    @api.depends('write_date')
    def _compute_updated_at(self):
        for seller in self:
            seller.updated_at = fields.Datetime.now()
    
    def action_submit_for_approval(self):
        """Submit seller for approval"""
        if not self.kyc_complete:
            raise UserError(_('Please complete KYC documents before submitting for approval.'))
        self.write({'state': 'pending'})
        self._notify_admin_submission()
    
    def action_approve(self):
        """Approve seller"""
        self.write({'state': 'approved'})
        self._ensure_seller_user()
        self._notify_seller_approval()
    
    def action_suspend(self):
        """Suspend seller"""
        self.write({'state': 'suspended'})
        self._notify_seller_suspension()
    
    def action_reject(self):
        """Reject seller"""
        self.write({'state': 'rejected'})
        self._notify_seller_rejection()
    
    def _ensure_seller_user(self):
        """Ensure seller has a portal user account"""
        pass  # Portal user creation can be implemented later
    
    def _notify_admin_submission(self):
        """Notify admin about new seller submission"""
        pass
    
    def _notify_seller_approval(self):
        """Notify seller about approval"""
        pass
    
    def _notify_seller_suspension(self):
        """Notify seller about suspension"""
        pass
    
    def _notify_seller_rejection(self):
        """Notify seller about rejection"""
        pass
    
    def get_social_channels(self):
        """Get social channels as dict"""
        try:
            return json.loads(self.social_channels or '{}')
        except:
            return {}
    
    def set_social_channels(self, channels_dict):
        """Set social channels from dict"""
        self.social_channels = json.dumps(channels_dict)
    
    @api.constrains('commission_value')
    def _check_commission_value(self):
        for seller in self:
            if seller.commission_type == 'percentage' and (seller.commission_value < 0 or seller.commission_value > 100):
                raise ValidationError(_('Commission percentage must be between 0 and 100.'))
            elif seller.commission_type == 'fixed' and seller.commission_value < 0:
                raise ValidationError(_('Fixed commission must be positive.'))


class MarketplaceSellerDocument(models.Model):
    _name = 'marketplace.seller.document'
    _description = 'Seller KYC Document'
    _order = 'create_date desc'

    name = fields.Char(string='Document Name', required=True)
    seller_id = fields.Many2one('marketplace.seller', string='Seller', required=True, ondelete='cascade')
    document_type_id = fields.Many2one(
        'marketplace.seller.document.type',
        string='Document Type',
        required=True,
    )
    file = fields.Binary(string='File', required=True)
    filename = fields.Char(string='Filename')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True)
    rejection_reason = fields.Text(string='Rejection Reason')
    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now, readonly=True)


class MarketplaceSellerDocumentType(models.Model):
    _name = 'marketplace.seller.document.type'
    _description = 'Seller Document Type'
    _order = 'sequence, name'

    name = fields.Char(string='Document Type', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    required = fields.Boolean(string='Required', default=False)
    description = fields.Text(string='Description')
