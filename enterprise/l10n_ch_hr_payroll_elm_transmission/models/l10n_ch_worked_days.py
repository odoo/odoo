# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrPayslipSwissWage(models.Model):
    _name = 'l10n.ch.swiss.wage.component'
    _description = 'Swiss Basic Wage Components'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Wage Type', readonly=False)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(string='Code', related='work_entry_type_id.code')
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Type', required=True, domain=lambda self: [("code", "in", self._get_allowed_work_entry_types())])
    salary_base = fields.Monetary(string="Base", readonly=False)
    rate = fields.Float(string="Factor", default=1)
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True, copy=True)
    contract_id = fields.Many2one(related='payslip_id.contract_id', string='Contract',
        help="The contract this worked days should be applied to")
    currency_id = fields.Many2one('res.currency', related='payslip_id.currency_id')

    @api.depends('payslip_id', 'salary_base', 'rate')
    def _compute_amount(self):
        for worked_days in self:
            if worked_days.payslip_id.edited or worked_days.payslip_id.state not in ['draft', 'verify']:
                continue
            worked_days.amount = worked_days.salary_base * worked_days.rate

    def _get_allowed_work_entry_types(self):
        return [
            "CH_1000", # Monthly Salary
            "CH_1005", # Hourly Salary
            "CH_1006", # Lesson Salary
            "CH_1065", # Overtime
            "CH_1061", # Overtime 125%
            "CH_1066", # Overtime 150%
            "CH_1068",  # Overtime 200%
            "CH_1071", # On-call duty 125%
            "CH_1075", # Night shift 110%
            "CH_ILLNESS", # Illness
            "CH_ACCIDENT", # Accident
            "CH_MATERNITY", # Maternity Leave
            "CH_MILITARY", # Military Leave
            "CH_ILLNESS_HOURLY", # Illness
            "CH_ACCIDENT_HOURLY", # Accident
            "CH_MATERNITY_HOURLY", # Maternity Leave
            "CH_MILITARY_HOURLY", # Military Leave
        ]
