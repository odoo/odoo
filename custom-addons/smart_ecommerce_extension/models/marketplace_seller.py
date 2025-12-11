# -*- coding: utf-8 -*-
# Part of SMART eCommerce Extension. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MarketplaceSeller(models.Model):
    _name = 'marketplace.seller'
    _description = 'Marketplace Seller'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Seller Name',
        compute='_compute_name',
        store=True,
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User Account',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='The user account associated with this seller',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        related='user_id.partner_id',
        store=True,
        readonly=True,
    )
    company_name = fields.Char(
        string='Company/Store Name',
        required=True,
        tracking=True,
        help='The business name displayed to customers',
    )
    
    # Contact Information
    email = fields.Char(
        related='partner_id.email',
        readonly=False,
        store=True,
    )
    phone = fields.Char(
        related='partner_id.phone',
        readonly=False,
        store=True,
    )
    street = fields.Char(related='partner_id.street', readonly=False)
    city = fields.Char(related='partner_id.city', readonly=False)
    country_id = fields.Many2one(related='partner_id.country_id', readonly=False)
    
    # KYC Documents
    kyc_doc = fields.Binary(
        string='KYC Document',
        attachment=True,
        help='Identity verification document (ID card, passport, business license)',
    )
    kyc_doc_filename = fields.Char(string='KYC Document Filename')
    kyc_verified = fields.Boolean(
        string='KYC Verified',
        default=False,
        tracking=True,
    )
    kyc_verified_date = fields.Date(
        string='KYC Verification Date',
        readonly=True,
    )
    kyc_verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        readonly=True,
    )
    
    # Business Documents
    business_license = fields.Binary(
        string='Business License',
        attachment=True,
    )
    business_license_filename = fields.Char(string='License Filename')
    tax_id = fields.Char(string='Tax ID / VAT Number')
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    rejection_reason = fields.Text(string='Rejection Reason')
    suspension_reason = fields.Text(string='Suspension Reason')
    
    # Financial Information
    bank_account = fields.Char(string='Bank Account Number')
    bank_name = fields.Char(string='Bank Name')
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        default=10.0,
        help='Platform commission percentage on each sale',
    )
    
    # Statistics (Computed)
    product_count = fields.Integer(
        string='Products',
        compute='_compute_statistics',
        store=True,
    )
    order_count = fields.Integer(
        string='Orders',
        compute='_compute_statistics',
    )
    total_sales = fields.Monetary(
        string='Total Sales',
        compute='_compute_statistics',
        currency_field='currency_id',
    )
    rating = fields.Float(
        string='Rating',
        default=0.0,
        digits=(2, 1),
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    
    # Timestamps
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    
    # Store Settings
    store_description = fields.Html(string='Store Description')
    store_logo = fields.Binary(string='Store Logo', attachment=True)
    store_banner = fields.Binary(string='Store Banner', attachment=True)
    
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('user_unique', 'UNIQUE(user_id)', 'A user can only have one seller account!'),
        ('company_name_unique', 'UNIQUE(company_name)', 'This store name is already taken!'),
    ]

    @api.depends('user_id', 'company_name')
    def _compute_name(self):
        for seller in self:
            if seller.company_name:
                seller.name = seller.company_name
            elif seller.user_id:
                seller.name = seller.user_id.name
            else:
                seller.name = _('New Seller')

    @api.depends('user_id')
    def _compute_statistics(self):
        """Compute seller statistics"""
        for seller in self:
            # Product count
            if hasattr(self.env['product.template'], 'seller_id'):
                seller.product_count = self.env['product.template'].search_count([
                    ('seller_id', '=', seller.id)
                ])
            else:
                seller.product_count = 0
            
            # Order statistics
            domain = [('partner_id', '=', seller.partner_id.id), ('state', 'in', ['sale', 'done'])]
            orders = self.env['sale.order'].sudo().search(domain)
            seller.order_count = len(orders)
            seller.total_sales = sum(orders.mapped('amount_total'))

    @api.constrains('commission_rate')
    def _check_commission_rate(self):
        for seller in self:
            if seller.commission_rate < 0 or seller.commission_rate > 100:
                raise ValidationError(_('Commission rate must be between 0 and 100%'))

    # ==========================================
    # STATE ACTIONS
    # ==========================================

    def action_submit_for_approval(self):
        """Submit seller profile for approval"""
        self.ensure_one()
        if not self.kyc_doc:
            raise UserError(_('Please upload KYC document before submitting for approval.'))
        self.write({'state': 'pending'})
        self.message_post(body=_('Seller profile submitted for approval.'))

    def action_approve(self):
        """Approve seller"""
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_date': fields.Datetime.now(),
            'approved_by': self.env.user.id,
        })
        self.message_post(body=_('Seller approved by %s') % self.env.user.name)
        
        # Send notification email
        template = self.env.ref('smart_ecommerce_extension.email_seller_approved', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_reject(self):
        """Reject seller - opens wizard for reason"""
        self.ensure_one()
        return {
            'name': _('Reject Seller'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.seller.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_seller_id': self.id},
        }

    def action_suspend(self):
        """Suspend seller - opens wizard for reason"""
        self.ensure_one()
        return {
            'name': _('Suspend Seller'),
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.seller.suspend.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_seller_id': self.id},
        }

    def action_reactivate(self):
        """Reactivate suspended seller"""
        self.ensure_one()
        self.write({
            'state': 'approved',
            'suspension_reason': False,
        })
        self.message_post(body=_('Seller reactivated by %s') % self.env.user.name)

    def action_verify_kyc(self):
        """Mark KYC as verified"""
        self.ensure_one()
        self.write({
            'kyc_verified': True,
            'kyc_verified_date': fields.Date.today(),
            'kyc_verified_by': self.env.user.id,
        })
        self.message_post(body=_('KYC verified by %s') % self.env.user.name)

    # ==========================================
    # PORTAL METHODS
    # ==========================================

    def get_portal_dashboard_data(self):
        """Get dashboard data for seller portal"""
        self.ensure_one()
        today = fields.Date.today()
        
        # Get orders this month
        first_of_month = today.replace(day=1)
        orders_this_month = self.env['sale.order'].sudo().search_count([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', first_of_month),
        ])
        
        # Get pending orders
        pending_orders = self.env['sale.order'].sudo().search_count([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'sale'),
        ])
        
        return {
            'seller': self,
            'product_count': self.product_count,
            'total_orders': self.order_count,
            'orders_this_month': orders_this_month,
            'pending_orders': pending_orders,
            'total_sales': self.total_sales,
            'rating': self.rating,
            'state': self.state,
        }

    def get_portal_orders(self, page=1, per_page=20):
        """Get orders for seller portal"""
        self.ensure_one()
        domain = [
            ('partner_id', '=', self.partner_id.id),
        ]
        
        total = self.env['sale.order'].sudo().search_count(domain)
        orders = self.env['sale.order'].sudo().search(
            domain,
            limit=per_page,
            offset=(page - 1) * per_page,
            order='date_order desc'
        )
        
        return {
            'orders': orders,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page,
        }

    def get_portal_payments(self, page=1, per_page=20):
        """Get payment history for seller portal"""
        self.ensure_one()
        # This would integrate with a payout system
        # For now, return order payments
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['sale', 'done']),
        ]
        
        orders = self.env['sale.order'].sudo().search(
            domain,
            limit=per_page,
            offset=(page - 1) * per_page,
            order='date_order desc'
        )
        
        payments = []
        for order in orders:
            payments.append({
                'order_id': order.id,
                'order_ref': order.name,
                'date': order.date_order,
                'amount': order.amount_total,
                'commission': order.amount_total * (self.commission_rate / 100),
                'net_amount': order.amount_total * (1 - self.commission_rate / 100),
                'currency': order.currency_id.name,
                'state': 'paid' if order.state == 'done' else 'pending',
            })
        
        return {
            'payments': payments,
            'page': page,
            'per_page': per_page,
        }


class MarketplaceSellerRejectWizard(models.TransientModel):
    _name = 'marketplace.seller.reject.wizard'
    _description = 'Reject Seller Wizard'

    seller_id = fields.Many2one('marketplace.seller', required=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_reject(self):
        self.ensure_one()
        self.seller_id.write({
            'state': 'rejected',
            'rejection_reason': self.reason,
        })
        self.seller_id.message_post(
            body=_('Seller rejected. Reason: %s') % self.reason
        )
        return {'type': 'ir.actions.act_window_close'}


class MarketplaceSellerSuspendWizard(models.TransientModel):
    _name = 'marketplace.seller.suspend.wizard'
    _description = 'Suspend Seller Wizard'

    seller_id = fields.Many2one('marketplace.seller', required=True)
    reason = fields.Text(string='Suspension Reason', required=True)

    def action_suspend(self):
        self.ensure_one()
        self.seller_id.write({
            'state': 'suspended',
            'suspension_reason': self.reason,
        })
        self.seller_id.message_post(
            body=_('Seller suspended. Reason: %s') % self.reason
        )
        return {'type': 'ir.actions.act_window_close'}

