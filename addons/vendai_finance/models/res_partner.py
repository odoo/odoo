from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # VendAI Fields
    vendai_is_lender = fields.Boolean(
        string='Is Lender',
        help='Mark this partner as a lending institution (Pezesha, Kuunda, etc.)'
    )
    vendai_credit_score = fields.Integer(
        string='Credit Score',
        compute='_compute_credit_score',
        help='Creditworthiness score (0-100)'
    )
    vendai_credit_score_manual = fields.Integer(
        string='Manual Credit Score',
        help='Optional override for the computed score (0-100). Leave blank for automatic scoring.'
    )
    vendai_total_facilities = fields.Integer(
        string='Total Facilities',
        compute='_compute_facility_stats'
    )
    vendai_active_facilities = fields.Integer(
        string='Active Facilities',
        compute='_compute_facility_stats'
    )
    vendai_total_borrowed = fields.Monetary(
        string='Total Borrowed',
        compute='_compute_facility_stats',
        currency_field='company_currency_id'
    )
    vendai_on_time_rate = fields.Float(
        string='On-Time Payment Rate (%)',
        compute='_compute_credit_score'
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id',
        readonly=True
    )
    
    @api.depends_context('uid')
    def _compute_credit_score(self):
        """Calculate credit score based on transaction history"""
        for partner in self:
            manual_score = partner.vendai_credit_score_manual
            if manual_score is not None:
                partner.vendai_credit_score = min(max(manual_score, 0), 100)
                partner.vendai_on_time_rate = 100.0
                continue

            if not partner.supplier_rank:
                partner.vendai_credit_score = 0
                partner.vendai_on_time_rate = 0.0
                continue
            
            # Get all completed POs as supplier
            completed_pos = self.env['purchase.order'].search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['purchase', 'done'])
            ])
            
            if not completed_pos:
                partner.vendai_credit_score = 50  # Default for new suppliers
                partner.vendai_on_time_rate = 0.0
                continue
            
            # Calculate scoring factors
            score = 0
            
            # 1. Transaction volume (max 30 points)
            total_volume = sum(completed_pos.mapped('amount_total'))
            if total_volume > 50000000:  # > 50M
                score += 30
            elif total_volume > 10000000:  # > 10M
                score += 25
            elif total_volume > 1000000:  # > 1M
                score += 20
            else:
                score += 10
            
            # 2. Transaction count (max 20 points)
            po_count = len(completed_pos)
            if po_count > 50:
                score += 20
            elif po_count > 20:
                score += 15
            elif po_count > 10:
                score += 10
            else:
                score += 5
            
            # 3. On-time payment rate (max 40 points)
            invoices = completed_pos.mapped('invoice_ids').filtered(
                lambda inv: inv.payment_state == 'paid'
            )
            if invoices:
                on_time_count = 0
                for invoice in invoices:
                    if invoice.invoice_date_due and invoice.payment_date:
                        if invoice.payment_date <= invoice.invoice_date_due:
                            on_time_count += 1
                
                on_time_rate = (on_time_count / len(invoices)) * 100
                partner.vendai_on_time_rate = on_time_rate
                score += (on_time_rate / 100) * 40  # Scale to 40 points
            else:
                partner.vendai_on_time_rate = 0.0
            
            # 4. Recency (max 10 points)
            latest_po = completed_pos.sorted('date_order', reverse=True)[0]
            days_since = (fields.Date.today() - latest_po.date_order.date()).days
            if days_since < 30:
                score += 10
            elif days_since < 90:
                score += 7
            elif days_since < 180:
                score += 5
            else:
                score += 2
            
            partner.vendai_credit_score = min(int(score), 100)
    
    @api.depends_context('uid')
    def _compute_facility_stats(self):
        """Compute facility statistics"""
        for partner in self:
            facilities = self.env['vendai.credit.facility'].search([
                ('supplier_id', '=', partner.id)
            ])
            
            partner.vendai_total_facilities = len(facilities)
            partner.vendai_active_facilities = len(facilities.filtered(
                lambda f: f.state in ['active', 'disbursed', 'repaying']
            ))
            partner.vendai_total_borrowed = sum(facilities.mapped('principal'))
    
    def action_view_credit_facilities(self):
        """View all credit facilities for this partner"""
        self.ensure_one()
        return {
            'name': 'Credit Facilities',
            'type': 'ir.actions.act_window',
            'res_model': 'vendai.credit.facility',
            'view_mode': 'list,form',
            'domain': [('supplier_id', '=', self.id)],
            'context': {'default_supplier_id': self.id}
        }
    
    def action_view_active_facilities(self):
        """View active credit facilities for this partner"""
        self.ensure_one()
        return {
            'name': 'Active Credit Facilities',
            'type': 'ir.actions.act_window',
            'res_model': 'vendai.credit.facility',
            'view_mode': 'list,form',
            'domain': [
                ('supplier_id', '=', self.id),
                ('state', 'in', ['active', 'disbursed', 'repaying'])
            ],
            'context': {'default_supplier_id': self.id}
        }
