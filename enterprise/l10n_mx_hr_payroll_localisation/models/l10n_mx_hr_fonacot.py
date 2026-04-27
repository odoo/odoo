# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrFonacot(models.Model):
    _name = 'l10n.mx.hr.fonacot'
    _description = 'fonacot'

    status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ], string="Status", required=True, default='in_progress')

    contract_id = fields.Many2one('hr.contract')
    currency_id = fields.Many2one(related='contract_id.currency_id')
    company_id = fields.Many2one(related='contract_id.company_id')

    extra_fixed_monthly_contribution = fields.Monetary(string="Extra Fixed Monthly Contribution")
    monthly_import = fields.Monetary(string="Import")

    _sql_constraints = [
        ('positive_monthly_import',
         'CHECK (monthly_import >= 0)',
         'The monthly import cannot be negative'),
        ('positive_extra_fixed_monthly_contribution',
         'CHECK (extra_fixed_monthly_contribution >= 0)',
         'The extra fixed monthly contribution cannot be negative'),
    ]
