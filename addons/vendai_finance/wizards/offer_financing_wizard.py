from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OfferFinancingWizard(models.TransientModel):
    _name = 'vendai.offer.financing.wizard'
    _description = 'Offer Financing to Supplier'
    
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        readonly=True
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
        readonly=True
    )
    po_amount = fields.Monetary(
        string='PO Amount',
        currency_field='currency_id',
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    credit_score = fields.Integer(
        related='supplier_id.vendai_credit_score',
        string='Credit Score'
    )
    financing_amount = fields.Monetary(
        string='Financing Amount',
        required=True,
        currency_field='currency_id'
    )
    max_financing_amount = fields.Monetary(
        string='Maximum Financing',
        compute='_compute_max_financing',
        currency_field='currency_id'
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
    estimated_interest = fields.Monetary(
        string='Estimated Interest',
        compute='_compute_estimated_interest',
        currency_field='currency_id'
    )
    total_repayment = fields.Monetary(
        string='Total Repayment',
        compute='_compute_estimated_interest',
        currency_field='currency_id'
    )
    buyer_guarantee = fields.Boolean(
        string='I guarantee payment to lender',
        default=True,
        required=True
    )
    
    @api.depends('po_amount', 'credit_score')
    def _compute_max_financing(self):
        """Calculate maximum financing based on PO amount and credit score"""
        for wizard in self:
            # Max financing is 40-60% of PO based on credit score
            if wizard.credit_score >= 80:
                percentage = 0.60  # 60% for excellent credit
            elif wizard.credit_score >= 70:
                percentage = 0.50
            elif wizard.credit_score >= 60:
                percentage = 0.45
            else:
                percentage = 0.40
            
            wizard.max_financing_amount = wizard.po_amount * percentage
    
    @api.depends('financing_amount', 'interest_rate', 'tenor_days')
    def _compute_estimated_interest(self):
        """Calculate interest and total repayment"""
        for wizard in self:
            if wizard.financing_amount and wizard.interest_rate:
                daily_rate = wizard.interest_rate / 100 / 365
                interest = wizard.financing_amount * daily_rate * wizard.tenor_days
                wizard.estimated_interest = interest
                wizard.total_repayment = wizard.financing_amount + interest
            else:
                wizard.estimated_interest = 0.0
                wizard.total_repayment = 0.0
    
    @api.constrains('financing_amount')
    def _check_financing_amount(self):
        """Validate financing amount"""
        for wizard in self:
            if wizard.financing_amount > wizard.max_financing_amount:
                raise UserError(_(
                    'Financing amount (KES %s) exceeds maximum allowed (KES %s) based on credit score.'
                ) % (f'{wizard.financing_amount:,.2f}', f'{wizard.max_financing_amount:,.2f}'))
            
            if wizard.financing_amount < 100000:
                raise UserError(_('Minimum financing amount is KES 100,000'))
    
    def action_offer_financing(self):
        """Create credit facility and offer to supplier"""
        self.ensure_one()
        
        if not self.buyer_guarantee:
            raise UserError(_('You must guarantee payment to proceed.'))
        
        # Create credit facility
        facility = self.env['vendai.credit.facility'].create({
            'purchase_order_id': self.purchase_order_id.id,
            'buyer_id': self.purchase_order_id.company_id.partner_id.id,
            'supplier_id': self.supplier_id.id,
            'po_amount': self.po_amount,
            'principal': self.financing_amount,
            'interest_rate': self.interest_rate,
            'tenor_days': self.tenor_days,
        })
        
        # Update PO
        self.purchase_order_id.write({
            'vendai_financing_offered': True,
            'vendai_financing_amount': self.financing_amount,
            'vendai_interest_rate': self.interest_rate,
            'vendai_tenor_days': self.tenor_days,
            'vendai_facility_id': facility.id,
        })
        
        # Change facility state to offered
        facility.action_offer_to_supplier()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Financing Offered'),
                'message': _('Financing offer sent to %s') % self.supplier_id.name,
                'type': 'success',
                'sticky': False,
            }
        }
