# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError


class l10nChCompensationFund(models.Model):
    _name = 'l10n.ch.compensation.fund'
    _description = 'Swiss: Family Allowance (CAF)'

    name = fields.Char(required=True)
    member_number = fields.Char()
    member_subnumber = fields.Char()
    # https://www.swissdec.ch/fileadmin/user_upload/_Datenempfaenger/Empfaengerliste.pdf
    insurance_company = fields.Char(required=True)
    insurance_code = fields.Char(required=True)
    caf_line_ids = fields.One2many('l10n.ch.compensation.fund.line', 'insurance_id')

    def _get_caf_rates(self, target, rate_type):
        if not self:
            return 0
        for line in self.caf_line_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line[rate_type]
        raise UserError(_('No CAF rates found for date %s', target))


class l10nChCompensationFundLine(models.Model):
    _name = 'l10n.ch.compensation.fund.line'
    _description = 'Swiss: Family Allowance Rate (CAF)'

    date_from = fields.Date(string="From", required=True, default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(string="To")
    insurance_id = fields.Many2one('l10n.ch.compensation.fund')
    employee_rate = fields.Float(string="Employee Rate (%)", digits='Payroll Rate', default=0.0)
    company_rate = fields.Float(string="Company Rate (%)", digits='Payroll Rate', default=0.421)
