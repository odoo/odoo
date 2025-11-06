from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # VendAI Fields
    vendai_financing_available = fields.Boolean(
        string='Financing Available',
        compute='_compute_financing_available',
        store=True
    )
    vendai_credit_score = fields.Integer(
        string='Supplier Credit Score',
        related='partner_id.vendai_credit_score',
        readonly=True
    )
    vendai_financing_offered = fields.Boolean(
        string='Financing Offered',
        default=False,
        tracking=True
    )
    vendai_financing_amount = fields.Monetary(
        string='Financing Amount',
        currency_field='currency_id'
    )
    vendai_interest_rate = fields.Float(
        string='Interest Rate (%)',
        default=4.5
    )
    vendai_tenor_days = fields.Integer(
        string='Tenor (Days)',
        default=60
    )
    vendai_facility_id = fields.Many2one(
        'vendai.credit.facility',
        string='Credit Facility',
        readonly=True
    )
    vendai_facility_state = fields.Selection(
        related='vendai_facility_id.state',
        string='Facility Status',
        readonly=True
    )
    vendai_estimated_interest = fields.Monetary(
        string='Estimated Interest',
        compute='_compute_estimated_interest',
        currency_field='currency_id'
    )
    
    @api.depends('partner_id', 'amount_total')
    def _compute_financing_available(self):
        """Check if supplier is eligible for financing"""
        for order in self:
            # Check if supplier has credit score
            if order.partner_id.vendai_credit_score >= 50:
                # Check if order amount meets minimum
                if order.amount_total >= 100000:  # KES 100K minimum
                    order.vendai_financing_available = True
                else:
                    order.vendai_financing_available = False
            else:
                order.vendai_financing_available = False
    
    @api.depends('vendai_financing_amount', 'vendai_interest_rate', 'vendai_tenor_days')
    def _compute_estimated_interest(self):
        """Calculate estimated interest cost"""
        for order in self:
            if order.vendai_financing_amount and order.vendai_interest_rate:
                # Simple interest: Principal * Rate * (Days/365)
                daily_rate = order.vendai_interest_rate / 100 / 365
                interest = order.vendai_financing_amount * daily_rate * order.vendai_tenor_days
                order.vendai_estimated_interest = interest
            else:
                order.vendai_estimated_interest = 0.0
    
    def action_offer_financing(self):
        """Open wizard to offer financing to supplier"""
        self.ensure_one()
        
        if not self.vendai_financing_available:
            raise UserError(_('Supplier is not eligible for financing. Credit score too low or order amount too small.'))
        
        # Calculate recommended financing amount (40% of PO value)
        recommended_amount = self.amount_total * 0.4
        
        return {
            'name': _('Offer Supplier Financing'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendai.offer.financing.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
                'default_supplier_id': self.partner_id.id,
                'default_po_amount': self.amount_total,
                'default_financing_amount': recommended_amount,
                'default_interest_rate': 4.5,
                'default_tenor_days': 60,
            }
        }
    
    def action_view_facility(self):
        """View associated credit facility"""
        self.ensure_one()
        return {
            'name': _('Credit Facility'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendai.credit.facility',
            'view_mode': 'form',
            'res_id': self.vendai_facility_id.id,
            'target': 'current',
        }
    
    def _prepare_invoice(self):
        """Override to pass VendAI facility info to invoice"""
        invoice_vals = super()._prepare_invoice()
        if self.vendai_facility_id:
            invoice_vals['vendai_facility_id'] = self.vendai_facility_id.id
        return invoice_vals
