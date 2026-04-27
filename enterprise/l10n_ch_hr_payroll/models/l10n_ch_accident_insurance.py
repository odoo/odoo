# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class l10nChAccidentInsurance(models.Model):
    # YTI TODO Rename into l10n.ch.laa.insurance
    _name = 'l10n.ch.accident.insurance'
    _description = 'Swiss: Accident Insurances (AAP/AANP)'

    name = fields.Char(required=True)
    customer_number = fields.Char(required=True)
    contract_number = fields.Char(required=True)
    # https://www.swissdec.ch/fileadmin/user_upload/_Datenempfaenger/Empfaengerliste.pdf
    insurance_company = fields.Char(required=True)
    insurance_code = fields.Char(required=True)
    insurance_company_address_id = fields.Many2one('res.partner')
    line_ids = fields.One2many('l10n.ch.accident.insurance.line', 'insurance_id')


class l10nChAccidentInsuranceLine(models.Model):
    _name = 'l10n.ch.accident.insurance.line'
    _description = 'Swiss: Accident Insurances Line (AAP/AANP)'
    _rec_name = 'solution_name'

    insurance_id = fields.Many2one('l10n.ch.accident.insurance')
    solution_name = fields.Char()
    solution_type = fields.Selection(selection=[
        ('A', 'A'),
        ('B', 'B')], required=True)
    solution_number = fields.Selection(selection=[
        ('0', '0 - Not insured (e.g. member of the board of directors not working in the company)'),
        ('1', '1 - Occupational and Non-Occupational Insured, with deductions'),
        ('2', '2 - Occupational and Non-Occupational Insured, without deductions'),
        ('3', '3 - Only Occupational Insured, without deductions (< 8 weekly hours)')], required=True, help="""
0: Not UVG insured (e.g. member of the board of directors not working in the company)
1: AAP and AANP insured, with AANP deduction
2: Insured AAP and AANP, without AANP deduction
3: Only AAP insured, so no AANP deduction (for employees whose weekly work is < 8 h))""")
    rate_ids = fields.One2many('l10n.ch.accident.insurance.line.rate', 'line_id')
    solution_code = fields.Char(compute='_compute_solution_code', store=True)

    @api.depends('solution_type', 'solution_number')
    def _compute_solution_code(self):
        for line in self:
            line.solution_code = line.solution_type + line.solution_number

    def _get_threshold(self, target):
        if not self:
            return 0
        for line in self.rate_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.threshold
        raise UserError(_('No AAP/AANP threshold found for date %s', target))

    def _get_occupational_rates(self, target, gender="male"):
        if not self:
            return 0, 0
        for line in self.rate_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                if gender == "male":
                    return line.occupational_male_rate, int(line.employer_occupational_part)
                if gender == "female":
                    return line.occupational_female_rate, int(line.employer_occupational_part)
                raise UserError(_('No found rate for gender %s', gender))
        raise UserError(_('No AAP rates found for date %s', target))

    def _get_non_occupational_rates(self, target, gender="male"):
        if not self:
            return 0, 0
        for line in self.rate_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                if gender == "male":
                    return line.non_occupational_male_rate, int(line.employer_non_occupational_part)
                if gender == "female":
                    return line.non_occupational_female_rate, int(line.employer_non_occupational_part)
                raise UserError(_('No found rate for gender %s', gender))
        raise UserError(_('No AANP rates found for date %s', target))


class l10nChAccidentInsuranceLineRate(models.Model):
    _name = 'l10n.ch.accident.insurance.line.rate'
    _description = 'Swiss: Accident Insurances Line Rate (AAP/AANP)'

    line_id = fields.Many2one('l10n.ch.accident.insurance.line')
    date_from = fields.Date(string="From", required=True, default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(string="To")
    threshold = fields.Float(default=148200)
    occupational_male_rate = fields.Float("Occupational Male Rate (%)", digits='Payroll Rate')
    occupational_female_rate = fields.Float("Occupational Female Rate (%)", digits='Payroll Rate')
    non_occupational_male_rate = fields.Float("Non-occupational Male Rate (%)", digits='Payroll Rate')
    non_occupational_female_rate = fields.Float("Non-occupational Female Rate (%)", digits='Payroll Rate')
    employer_occupational_part = fields.Selection([
        ('0', '0 %'),
        ('50', '50 %'),
        ('100', '100 %'),
    ], string="Company Occupational Part", default='50')
    employer_non_occupational_part = fields.Selection([
        ('0', '0 %'),
        ('50', '50 %'),
        ('100', '100 %'),
    ], string="Company Non Occupational Part", default='50')
