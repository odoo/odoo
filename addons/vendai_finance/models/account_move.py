# Account Move Extension - Handle tripartite payment split

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    vendai_facility_id = fields.Many2one(
        'vendai.credit.facility',
        string='VendAI Facility',
        readonly=True
    )
    vendai_has_facility = fields.Boolean(
        compute='_compute_vendai_has_facility',
        string='Has Financing'
    )
    
    @api.depends('vendai_facility_id')
    def _compute_vendai_has_facility(self):
        for move in self:
            move.vendai_has_facility = bool(move.vendai_facility_id)
    
    def action_post(self):
        """Override to trigger repayment when invoice paid"""
        res = super().action_post()
        
        # Check for VendAI facility repayment
        for move in self:
            if move.vendai_facility_id and move.payment_state == 'paid':
                move.vendai_facility_id.action_process_repayment(move)
        
        return res
