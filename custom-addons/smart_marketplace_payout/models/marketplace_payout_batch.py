# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class MarketplacePayoutBatch(models.Model):
    _name = 'marketplace.payout.batch'
    _description = 'Marketplace Payout Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, default=lambda self: _('New'), readonly=True, copy=False)
    seller_id = fields.Many2one(
        'marketplace.seller',
        string='Seller',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    
    # Amounts
    amount = fields.Monetary(string='Total Amount', compute='_compute_amounts', store=True)
    commission_amount = fields.Monetary(string='Commission', compute='_compute_amounts', store=True)
    fee = fields.Monetary(string='Fee', default=0.0)
    net_amount = fields.Monetary(string='Net Amount', compute='_compute_amounts', store=True)
    currency_id = fields.Many2one('res.currency', related='seller_id.currency_id', store=True)
    
    # Status
    status = fields.Selection([
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ], string='Status', default='pending', required=True, tracking=True)
    
    # Transfer
    transfer_reference = fields.Char(string='Transfer Reference')
    transfer_date = fields.Date(string='Transfer Date')
    transfer_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('manual', 'Manual'),
    ], string='Transfer Method', default='bank_transfer')
    
    # Relations
    order_ids = fields.Many2many(
        'sale.order',
        'payout_batch_order_rel',
        'payout_id',
        'order_id',
        string='Orders',
    )
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    
    # Additional
    notes = fields.Text(string='Notes')
    create_date = fields.Datetime(string='Created At', readonly=True)
    write_date = fields.Datetime(string='Updated At', readonly=True)
    
    @api.depends('order_ids', 'order_ids.amount_total', 'order_ids.commission_amount', 'fee')
    def _compute_amounts(self):
        for payout in self:
            orders = payout.order_ids.filtered(lambda o: o.state in ('sale', 'done'))
            payout.amount = sum(orders.mapped('amount_total'))
            payout.commission_amount = sum(orders.mapped('commission_amount'))
            payout.net_amount = payout.amount - payout.commission_amount - payout.fee
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('marketplace.payout.batch') or _('New')
        return super().create(vals)
    
    def action_process(self):
        """Process payout - create accounting entries"""
        for payout in self:
            if payout.status != 'pending':
                raise UserError(_('Only pending payouts can be processed.'))
            
            # Create journal entry
            payout._create_accounting_entry()
            payout.write({'status': 'processed'})
    
    def action_mark_paid(self):
        """Mark payout as paid"""
        for payout in self:
            if payout.status != 'processed':
                raise UserError(_('Payout must be processed before marking as paid.'))
            payout.write({
                'status': 'paid',
                'transfer_date': fields.Date.today(),
            })
    
    def _create_accounting_entry(self):
        """Create accounting journal entry for payout"""
        # This is a simplified version - should be customized based on accounting requirements
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        
        if not journal:
            raise UserError(_('No bank journal found. Please configure one.'))
        
        # Create move
        move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'Payout: {self.name}',
            'line_ids': [
                (0, 0, {
                    'account_id': self._get_payout_account().id,
                    'debit': self.net_amount,
                    'credit': 0,
                    'name': f'Payout to {self.seller_id.name}',
                }),
                (0, 0, {
                    'account_id': journal.default_account_id.id,
                    'debit': 0,
                    'credit': self.net_amount,
                    'name': f'Payout to {self.seller_id.name}',
                }),
            ],
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.write({'move_id': move.id})
    
    def _get_payout_account(self):
        """Get the account for payouts (should be configured)"""
        # Default to seller's partner account receivable
        return self.seller_id.partner_id.property_account_receivable_id or \
               self.env['account.account'].search([
                   ('code', '=', '400000'),  # Default revenue account
                   ('company_id', '=', self.env.company.id),
               ], limit=1)
    
    @api.model
    def cron_generate_payouts(self):
        """Cron job to generate payouts for sellers"""
        # Get all approved sellers
        sellers = self.env['marketplace.seller'].search([('state', '=', 'approved')])
        
        # Default period: last 30 days
        date_to = fields.Date.today()
        date_from = date_to - timedelta(days=30)
        
        for seller in sellers:
            # Get unpaid orders
            orders = self.env['sale.order'].search([
                ('seller_id', '=', seller.id),
                ('state', 'in', ('sale', 'done')),
                ('date_order', '>=', date_from),
                ('date_order', '<=', date_to),
                ('id', 'not in', self.search([]).mapped('order_ids').ids),  # Not in existing payouts
            ])
            
            if orders:
                # Create payout batch
                self.create({
                    'seller_id': seller.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'order_ids': [(6, 0, orders.ids)],
                })
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for payout in self:
            if payout.date_from > payout.date_to:
                raise ValidationError(_('From Date must be before To Date.'))

