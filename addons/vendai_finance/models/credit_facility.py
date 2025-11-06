from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import requests
import logging

_logger = logging.getLogger(__name__)


class CreditFacility(models.Model):
    _name = 'vendai.credit.facility'
    _description = 'VendAI Credit Facility'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(
        string='Facility Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('offered', 'Offered to Supplier'),
        ('accepted', 'Accepted by Supplier'),
        ('approved', 'Approved by Lender'),
        ('disbursed', 'Disbursed'),
        ('active', 'Active'),
        ('repaying', 'Repaying'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Parties
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='restrict'
    )
    buyer_id = fields.Many2one(
        'res.partner',
        string='Buyer (Guarantor)',
        required=True
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier (Borrower)',
        required=True
    )
    lender_id = fields.Many2one(
        'res.partner',
        string='Lender',
        domain=[('vendai_is_lender', '=', True)]
    )
    
    # Financial Terms
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    po_amount = fields.Monetary(
        string='PO Amount',
        currency_field='currency_id',
        required=True
    )
    principal = fields.Monetary(
        string='Financing Amount (Principal)',
        currency_field='currency_id',
        required=True
    )
    interest_rate = fields.Float(
        string='Interest Rate (%)',
        required=True,
        default=4.5
    )
    tenor_days = fields.Integer(
        string='Tenor (Days)',
        required=True,
        default=60
    )
    interest_amount = fields.Monetary(
        string='Total Interest',
        compute='_compute_interest_amount',
        store=True,
        currency_field='currency_id'
    )
    total_repayment = fields.Monetary(
        string='Total Repayment',
        compute='_compute_total_repayment',
        store=True,
        currency_field='currency_id'
    )
    
    # Dates
    offered_date = fields.Datetime(string='Offered Date', readonly=True)
    accepted_date = fields.Datetime(string='Accepted Date', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    disbursed_date = fields.Datetime(string='Disbursed Date', readonly=True)
    due_date = fields.Date(string='Due Date', compute='_compute_due_date', store=True)
    closed_date = fields.Datetime(string='Closed Date', readonly=True)
    
    # Disbursement Info
    supplier_bank_account = fields.Char(string='Supplier Bank Account')
    supplier_bank_name = fields.Char(string='Bank Name')
    disbursement_ref = fields.Char(string='Disbursement Reference', readonly=True)
    disbursement_method = fields.Selection([
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('rtgs', 'RTGS'),
        ('eft', 'EFT'),
    ], string='Disbursement Method', default='bank')
    
    # Repayment Info
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    repayment_amount = fields.Monetary(
        string='Amount Repaid',
        currency_field='currency_id',
        readonly=True
    )
    repayment_date = fields.Datetime(string='Repayment Date', readonly=True)
    repayment_ref = fields.Char(string='Repayment Reference', readonly=True)
    
    # Lender API Integration
    lender_facility_id = fields.Char(string='Lender Facility ID', readonly=True)
    lender_api_url = fields.Char(string='Lender API URL')
    
    @api.depends('principal', 'interest_rate', 'tenor_days')
    def _compute_interest_amount(self):
        """Calculate simple interest"""
        for facility in self:
            if facility.principal and facility.interest_rate:
                # Simple interest: P * R * (T/365)
                daily_rate = facility.interest_rate / 100 / 365
                facility.interest_amount = facility.principal * daily_rate * facility.tenor_days
            else:
                facility.interest_amount = 0.0
    
    @api.depends('principal', 'interest_amount')
    def _compute_total_repayment(self):
        """Calculate total repayment amount"""
        for facility in self:
            facility.total_repayment = facility.principal + facility.interest_amount
    
    @api.depends('disbursed_date', 'tenor_days')
    def _compute_due_date(self):
        """Calculate due date from disbursement + tenor"""
        for facility in self:
            if facility.disbursed_date:
                facility.due_date = facility.disbursed_date.date() + timedelta(days=facility.tenor_days)
            else:
                facility.due_date = False

    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence number"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('vendai.credit.facility') or _('New')
        return super().create(vals_list)

    def action_offer_to_supplier(self):
        """Buyer offers financing to supplier"""
        self.ensure_one()
        self.write({
            'state': 'offered',
            'offered_date': fields.Datetime.now()
        })
        # Send notification to supplier
        self.message_post(
            body=_('Financing offer sent to %s for KES %s') % (
                self.supplier_id.name,
                f'{self.principal:,.2f}'
            ),
            subject=_('Financing Offered')
        )
    
    def action_accept_by_supplier(self):
        """Supplier accepts financing offer"""
        self.ensure_one()
        if self.state != 'offered':
            raise UserError(_('Can only accept offers in Offered state'))
        
        self.write({
            'state': 'accepted',
            'accepted_date': fields.Datetime.now()
        })
        
        # Auto-submit to lender for approval
        self.action_submit_to_lender()
    
    def action_submit_to_lender(self):
        """Submit to lender (Pezesha/Kuunda) for approval"""
        self.ensure_one()
        
        # Call Pezesha API (Patascore) - Demo mode for now
        try:
            response = self._call_lender_api('submit')
            if response.get('approved'):
                self.write({
                    'state': 'approved',
                    'approved_date': fields.Datetime.now(),
                    'lender_facility_id': response.get('facility_id'),
                })
                # Auto-trigger disbursement
                self.action_disburse()
        except Exception as e:
            _logger.error(f'Lender API error: {e}')
            raise UserError(_('Failed to submit to lender: %s') % str(e))
    
    def action_disburse(self):
        """Disburse funds to supplier"""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Can only disburse approved facilities'))
        
        # Call lender API to trigger disbursement
        try:
            response = self._call_lender_api('disburse')
            self.write({
                'state': 'disbursed',
                'disbursed_date': fields.Datetime.now(),
                'disbursement_ref': response.get('disbursement_ref')
            })
            self.message_post(
                body=_('Funds disbursed: KES %s to %s') % (
                    f'{self.principal:,.2f}',
                    self.supplier_bank_account
                ),
                subject=_('Disbursement Completed')
            )
        except Exception as e:
            _logger.error(f'Disbursement error: {e}')
            raise UserError(_('Disbursement failed: %s') % str(e))
    
    def action_process_repayment(self):
        """Process repayment - manually mark as repaying"""
        self.ensure_one()
        if self.state not in ('disbursed', 'active'):
            raise UserError(_('Can only process repayment for disbursed/active facilities'))
        
        self.write({
            'state': 'repaying'
        })
        
        self.message_post(
            body=_('Repayment process initiated'),
            subject=_('Repayment Started')
        )
        
        # Split payment will be handled by account.move extension
        
    def action_close_facility(self):
        """Close facility after full repayment"""
        self.ensure_one()
        self.write({
            'state': 'closed',
            'closed_date': fields.Datetime.now()
        })
        self.message_post(
            body=_('Facility closed. Total repaid: KES %s') % f'{self.total_repayment:,.2f}',
            subject=_('Facility Closed')
        )
    
    def action_cancel(self):
        """Cancel the facility"""
        self.ensure_one()
        if self.state in ('disbursed', 'active', 'repaying', 'closed'):
            raise UserError(_('Cannot cancel a facility that has been disbursed or is already closed'))
        
        self.write({
            'state': 'cancelled'
        })
        self.message_post(
            body=_('Facility cancelled'),
            subject=_('Facility Cancelled')
        )
    
    def _call_lender_api(self, action):
        """Call Pezesha/Kuunda API - Demo mode returns mock data"""
        # TODO: Implement actual API integration
        # For now, simulate approval
        if action == 'submit':
            return {
                'approved': True,
                'facility_id': f'PEZ-{self.name}',
                'credit_score': self.supplier_id.vendai_credit_score
            }
        elif action == 'disburse':
            return {
                'disbursement_ref': f'DISB-{self.name}-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            }
        return {}
    
    def action_view_purchase_order(self):
        """View the related purchase order"""
        self.ensure_one()
        return {
            'name': 'Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
        }
    
    def action_view_invoice(self):
        """View the related invoice"""
        self.ensure_one()
        if not self.invoice_id:
            return {}
        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }
