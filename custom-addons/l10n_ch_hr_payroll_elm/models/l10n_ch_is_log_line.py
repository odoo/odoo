# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nCHPayslipISLogLine(models.Model):
    _name = 'hr.payslip.is.log.line'
    _description = 'IS Log lines'

    is_code = fields.Char()
    code = fields.Char()
    amount = fields.Float()
    payslip_id = fields.Many2one('hr.payslip')
    is_correction = fields.Boolean()
    corrected_slip_id = fields.Many2one('hr.payslip')
    date = fields.Date()
