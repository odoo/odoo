# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class l10nChSocialInsurance(models.Model):
    _name = 'l10n.ch.social.insurance'
    _description = 'Swiss: Social Insurances (AVS, AC)'

    name = fields.Char(required=True)
    member_number = fields.Char()
    member_subnumber = fields.Char()
    # https://www.swissdec.ch/fileadmin/user_upload/_Datenempfaenger/Empfaengerliste.pdf
    insurance_company = fields.Char(required=True)
    insurance_code = fields.Char(required=True)
    avs_line_ids = fields.One2many('l10n.ch.social.insurance.avs.line', 'insurance_id')
    ac_line_ids = fields.One2many('l10n.ch.social.insurance.ac.line', 'insurance_id')
    l10n_ch_avs_rente_ids = fields.One2many('l10n.ch.social.insurance.avs.retirement.rente', 'insurance_id')
    l10n_ch_avs_ac_threshold_ids = fields.One2many('l10n.ch.social.insurance.avs.ac.threshold', 'insurance_id')
    l10n_ch_avs_acc_threshold_ids = fields.One2many('l10n.ch.social.insurance.avs.acc.threshold', 'insurance_id')
    age_start = fields.Integer(string="Start of the obligation to contribute to the AVS", default=18, required=True)
    age_stop_male = fields.Integer(string="Start of retirement age for men", default=65, required=True)
    age_stop_female = fields.Integer(string="Start of retirement age for women", default=64, required=True)
    laa_insurance_id = fields.Many2one("l10n.ch.accident.insurance", string="Company LAA Insurance")
    laa_insurance_from = fields.Date(string="LAA: Valid as of")
    lpp_insurance_id = fields.Many2one("l10n.ch.lpp.insurance", string="Company LPP Insurance")
    lpp_insurance_from = fields.Date(string="LPP: Valid as of")

    @api.depends('insurance_company')
    def _compute_insurance_code(self):
        for insurance in self:
            insurance.insurance_code = insurance.insurance_company

    def _get_avs_rates(self, target):
        if not self:
            return 0, 0
        for line in self.avs_line_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.employee_rate, line.employer_rate
        raise UserError(_('No AVS rates found for date %s', target))

    def _get_ac_rates(self, target):
        if not self:
            return 0, 0
        for line in self.ac_line_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.employee_rate, line.employer_rate
        raise UserError(_('No AC rates found for date %s', target))

    def _get_additional_ac_rates(self, target):
        if not self:
            return 0, 0
        for line in self.ac_line_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.employee_additional_rate, line.employer_additional_rate
        raise UserError(_('No AC rates found for date %s', target))

    def _get_retirement_rente(self, target):
        if not self:
            return 0.0
        for line in self.l10n_ch_avs_rente_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.amount
        raise UserError(_('No retirement exoneration amounts found for date date %s', target))

    def _get_ac_threshold(self, target):
        if not self:
            return 0.0
        for line in self.l10n_ch_avs_ac_threshold_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.amount
        raise UserError(_('No AC threshold rates found for date %s', target))

    def _get_acc_threshold(self, target):
        if not self:
            return 0.0
        for line in self.l10n_ch_avs_acc_threshold_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line.amount
        raise UserError(_('No ACC threshold rates found for date %s', target))


class l10nChSocialInsuranceAVSLine(models.Model):
    _name = 'l10n.ch.social.insurance.avs.line'
    _description = 'Swiss: Social Insurances - AVS Line'

    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To")
    insurance_id = fields.Many2one('l10n.ch.social.insurance')
    employee_rate = fields.Float(string="Employee Rate (%)", default=5.3)
    employer_rate = fields.Float(string="Company Rate (%)", default=5.3)

class l10nChSocialInsuranceACLine(models.Model):
    _name = 'l10n.ch.social.insurance.ac.line'
    _description = 'Swiss: Social Insurances - AC Line'

    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To")
    insurance_id = fields.Many2one('l10n.ch.social.insurance')
    employee_rate = fields.Float(string="Employee Rate (%)", digits='Payroll Rate', default=1.1)
    employer_rate = fields.Float(string="Company Rate (%)", digits='Payroll Rate', default=1.1)
    employee_additional_rate = fields.Float(string="Employee Additional Rate (%)", digits='Payroll Rate', default=0)
    employer_additional_rate = fields.Float(string="Company Additional Rate (%)", digits='Payroll Rate', default=0)


class l10nChSocialInsuranceRetirementRente(models.Model):
    _name = 'l10n.ch.social.insurance.avs.retirement.rente'
    _description = 'Swiss: Retired Employees Exoneration'

    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To")
    insurance_id = fields.Many2one('l10n.ch.social.insurance')
    amount = fields.Float(string="Amount", default=1400)


class l10nChSocialInsuranceACThreshold(models.Model):
    _name = 'l10n.ch.social.insurance.avs.ac.threshold'
    _description = 'Swiss: AC: Rate Threshold'

    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To")
    insurance_id = fields.Many2one('l10n.ch.social.insurance')
    amount = fields.Float(string="Amount", default=148200)


class l10nChSocialInsuranceACCThreshold(models.Model):
    _name = 'l10n.ch.social.insurance.avs.acc.threshold'
    _description = 'Swiss: ACC: Rate Threshold'

    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To")
    insurance_id = fields.Many2one('l10n.ch.social.insurance')
    amount = fields.Float(string="Amount", default=370500)
