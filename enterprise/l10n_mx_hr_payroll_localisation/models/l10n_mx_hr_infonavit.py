# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrInfonavit(models.Model):
    _name = 'l10n.mx.hr.infonavit'
    _description = 'infonavit'

    status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ], string="Status", required=True, default='in_progress')

    contract_id = fields.Many2one('hr.contract')
    currency_id = fields.Many2one(related='contract_id.currency_id')
    company_id = fields.Many2one(related='contract_id.company_id')

    monthly_insurance = fields.Monetary(string="Monthly Insurance")
    extra_fixed_monthly_contribution = fields.Monetary(string="Extra Fixed Monthly Contribution")

    infonavit_type = fields.Selection([
        ('fixed_monetary_fee', 'Fixed Monetary Fee'),
        ('percentage', 'Percentage'),
        ('discount_factor', 'Discount Factor'),
    ], string="Type", required=True, default='fixed_monetary_fee')
    fixed_monetary_fee = fields.Monetary(string="Fixed Monetary Fee")
    percentage = fields.Float(string="Percentage")
    discount_factor = fields.Float(string="Discount Factor")

    _sql_constraints = [
        ('percentage',
         'CHECK (0 <= percentage AND percentage <= 100)',
         'The percentage must be between 0 and 100'),
        ('positive_monthly_insurance',
         'CHECK (monthly_insurance >= 0)',
         'The monthly insurance cannot be negative'),
        ('positive_extra_fixed_monthly_contribution',
         'CHECK (extra_fixed_monthly_contribution >= 0)',
         'The extra fixed monthly contribution cannot be negative'),
        ('positive_fixed_monetary_fee',
         'CHECK (fixed_monetary_fee >= 0)',
         'The fixed monetary fee cannot be negative'),
        ('positive_discount_factor',
         'CHECK (discount_factor >= 0)',
         'The discount factor cannot be negative'),
    ]
