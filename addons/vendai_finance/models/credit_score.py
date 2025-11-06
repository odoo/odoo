# Credit Score Model - Placeholder
# This will store historical credit score calculations

from odoo import models, fields


class CreditScore(models.Model):
    _name = 'vendai.credit.score'
    _description = 'Credit Score History'
    _order = 'calculation_date desc'
    
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True)
    score = fields.Integer(string='Score', required=True)
    calculation_date = fields.Datetime(string='Calculated At', default=fields.Datetime.now)
    notes = fields.Text(string='Calculation Notes')
