from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AcceptFinancingWizard(models.TransientModel):
    _name = 'vendai.accept.financing.wizard'
    _description = 'Accept Financing Offer'
    
    facility_id = fields.Many2one('vendai.credit.facility', string='Credit Facility', required=True)
    buyer_id = fields.Many2one('res.partner', string='Buyer', related='facility_id.buyer_id', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', related='facility_id.purchase_order_id', readonly=True)
    principal = fields.Monetary(string='Principal Amount', related='facility_id.principal', readonly=True)
    interest_rate = fields.Float(string='Interest Rate', related='facility_id.interest_rate', readonly=True)
    tenor_days = fields.Integer(string='Tenor (Days)', related='facility_id.tenor_days', readonly=True)
    total_repayment = fields.Monetary(string='Total Repayment', related='facility_id.total_repayment', readonly=True)
    currency_id = fields.Many2one('res.currency', related='facility_id.currency_id', readonly=True)
    
    # Bank details
    bank_account_number = fields.Char(string='Bank Account Number', required=True)
    bank_name = fields.Char(string='Bank Name', required=True)
    bank_branch = fields.Char(string='Bank Branch')
    account_holder_name = fields.Char(string='Account Holder Name', required=True)
    
    accept_terms = fields.Boolean(string='I accept the terms and conditions', default=False)
    
    @api.model
    def default_get(self, fields_list):
        """Set default account holder name from supplier"""
        res = super().default_get(fields_list)
        if 'facility_id' in res:
            facility = self.env['vendai.credit.facility'].browse(res['facility_id'])
            if 'account_holder_name' in fields_list and facility.supplier_id:
                res['account_holder_name'] = facility.supplier_id.name
        return res
    
    def action_accept(self):
        """Accept financing offer and submit to lender"""
        self.ensure_one()
        
        if not self.accept_terms:
            raise UserError(_('You must accept the terms and conditions to proceed.'))
        
        # Update facility with bank details
        self.facility_id.write({
            'supplier_bank_account': self.bank_account_number,
            'supplier_bank_name': self.bank_name,
        })
        
        # Accept the facility
        self.facility_id.action_accept_by_supplier()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Financing Accepted'),
                'message': _('Your acceptance has been submitted to the lender for approval.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_decline(self):
        """Decline the financing offer"""
        self.ensure_one()
        
        self.facility_id.write({'state': 'cancelled'})
        self.facility_id.message_post(body=_('The financing offer was declined by the supplier.'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Offer Declined'),
                'message': _('The financing offer has been declined.'),
                'type': 'warning',
                'sticky': False,
            }
        }
