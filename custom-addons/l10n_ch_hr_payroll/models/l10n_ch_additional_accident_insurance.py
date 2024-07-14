# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class l10nChAdditionalAccidentInsurance(models.Model):
    _name = 'l10n.ch.additional.accident.insurance'
    _description = 'Swiss: Additional Accident Insurances (LAAC)'

    name = fields.Char(required=True)
    customer_number = fields.Char(required=True)
    contract_number = fields.Char(required=True)
    # https://www.swissdec.ch/fileadmin/user_upload/_Datenempfaenger/Empfaengerliste.pdf
    insurance_company = fields.Selection([
        ('S14', 'AXA Versicherungen AG'),
        ('S22', 'Allianz Suisse'),
        ('S6', 'Baloise Versicherungen AG'),
        ('S26', 'Branchen Versicherung Genossenschaft'),
        ('S10058', 'elipsLife'),
        ('046.000', 'Gastrosocial'),
        ('S21', 'GENERALI Versicherungen'),
        ('S270', 'Groupe Mutuel'),
        ('S264', 'Helsana Versicherungen AG'),
        ('S23', 'Helvetia'),
        ('S329', 'Hotela Assurances SA'),
        ('K329', 'Hotela Caisse Maladie'),
        ('S208', 'ÖKK Kranken- und Unfallversicherungen AG (ab Deklarationsjahr 2023)'),
        ('S1', 'Schweizerische Mobiliar Versicherungsgesellschaft AG'),
        ('S225', 'Sodalis'),
        ('S95', 'SOLIDA Versicherungen AG'),
        ('S999', 'Suva'),
        ('S122', 'Swica Versicherungen'),
        ('S205', 'Sympany'),
        ('S116', 'Vaudoise Assurances / Vaudoise Versicherungen'),
        ('S94', 'Visana Versicherungen AG'),
        ('S12', 'Zurich Versicherung')
    ])
    insurance_code = fields.Char(compute='_compute_insurance_code')
    insurance_company_address_id = fields.Many2one('res.partner')
    line_ids = fields.One2many('l10n.ch.additional.accident.insurance.line', 'insurance_id')

    @api.depends('insurance_company')
    def _compute_insurance_code(self):
        for insurance in self:
            insurance.insurance_code = insurance.insurance_company


class l10nChAdditionalAccidentInsuranceLine(models.Model):
    _name = 'l10n.ch.additional.accident.insurance.line'
    _description = 'Swiss: Additional Accident Insurances Line (LAAC)'
    _rec_name = 'solution_name'

    insurance_id = fields.Many2one('l10n.ch.additional.accident.insurance')
    solution_name = fields.Char()
    solution_type = fields.Selection(selection=[
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')], required=True)
    solution_number = fields.Selection(selection=[
        ('0', '0'),
        ('1', '1'),
        ('2', '2')], required=True)
    rate_ids = fields.One2many('l10n.ch.additional.accident.insurance.line.rate', 'line_id')

    def _get_threshold(self, target):
        if not self:
            return 0
        valid_rates = self.env['l10n.ch.additional.accident.insurance.line.rate']
        for rate in self.rate_ids:
            if rate.date_from <= target and (not rate.date_to or target <= rate.date_to):
                valid_rates += rate
        if valid_rates:
            return max(valid_rates.mapped('wage_to'))
        raise UserError(_('No LAAC threshold found for date %s', target))

    def _get_rates(self, target, gender="male"):
        if not self:
            return 0, 0, 0, 0
        for rate in self.rate_ids:
            if rate.date_from <= target and (not rate.date_to or target <= rate.date_to):
                if gender == "male":
                    return rate.wage_from, rate.wage_to, rate.male_rate, int(rate.employer_part)
                if gender == "female":
                    return rate.wage_from, rate.wage_to, rate.female_rate, int(rate.employer_part)
                raise UserError(_('No found rate for gender %s', gender))
        raise UserError(_('No LAAC rates found for date %s', target))


class l10nChAdditionalAccidentInsuranceLineRate(models.Model):
    _name = 'l10n.ch.additional.accident.insurance.line.rate'
    _description = 'Swiss: Accident Additional Insurances Line Rate (LAAC)'

    line_id = fields.Many2one('l10n.ch.additional.accident.insurance.line')
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To")
    wage_from = fields.Float(string="Wage From")
    wage_to = fields.Float(string="Wage To")
    male_rate = fields.Float(string="Male Rate (%)", digits='Payroll Rate')
    female_rate = fields.Float(string="Female Rate (%)", digits='Payroll Rate')
    employer_part = fields.Selection([
        ('0', '0 %'),
        ('50', '50 %'),
        ('100', '100 %'),
    ], default='50')
