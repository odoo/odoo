# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_contract_type_domain(self):
        if self.env.company.country_id.code == "CH":
            return [('country_id', '=', self.env.company.country_id.id)]
        return []

    contract_type_id = fields.Many2one(domain=_get_contract_type_domain)
    l10n_ch_job_type = fields.Selection([
        ('highestCadre', 'Top Management'),
        ('middleCadre', 'Middle Management'),
        ('lowerCadre', 'Lower Management'),
        ('lowestCadre', 'Responsible for carrying out the work'),
        ('noCadre', 'Without management function'),
    ], default='noCadre', string="Job Type")
    l10n_ch_thirteen_month = fields.Boolean(
        string="Has 13th Month")
    l10n_ch_social_insurance_id = fields.Many2one(
        'l10n.ch.social.insurance', string="AVS/AC Insurance")
    l10n_ch_lpp_insurance_id = fields.Many2one(
        'l10n.ch.lpp.insurance', string="LPP Insurance")
    l10n_ch_accident_insurance_line_id = fields.Many2one(
        'l10n.ch.accident.insurance.line', string="LAA Insurance")
    l10n_ch_additional_accident_insurance_line_ids = fields.Many2many(
        'l10n.ch.additional.accident.insurance.line', string="LAAC Insurances")
    l10n_ch_sickness_insurance_line_ids = fields.Many2many(
        'l10n.ch.sickness.insurance.line', string="IJM Insurances")
    l10n_ch_compensation_fund_id = fields.Many2one(
        'l10n.ch.compensation.fund', string="Family Compensation Fund")
    l10n_ch_lesson_wage = fields.Float('Lesson Wage', tracking=True, help="Employee's gross wage by lesson.")
    l10n_ch_contractual_13th_month_rate = fields.Float("Contractual allowances for 13th/14th month", digits='Payroll Rate', default=8.3333)
    l10n_ch_location_unit_id = fields.Many2one("l10n.ch.location.unit", string="Workplace")
    l10n_ch_avs_status = fields.Selection([
        ('youth', 'Youth'),
        ('exempted', 'Exempted'),
        ('retired', 'Retired'),
    ], string="AVS Special Status")
    l10n_ch_yearly_holidays = fields.Integer(string="Yearly Holidays Count", default=20)
    l10n_ch_yearly_paid_public_holidays = fields.Integer(default=10, string="Yearly Paid Public Holidays Count")
    l10n_ch_lpp_not_insured = fields.Boolean(string="Not LPP Insured")
    l10n_ch_has_withholding_tax = fields.Boolean(related="employee_id.l10n_ch_has_withholding_tax")
    l10n_ch_other_employers = fields.Boolean(string="Other Employers")
    l10n_ch_current_occupation_rate = fields.Float(string="Current Occupation rate", compute='_compute_l10n_ch_current_occupation_rate', store=True, readonly=False)
    l10n_ch_other_employers_occupation_rate = fields.Float(string="Occupation rate other employers")
    l10n_ch_total_occupation_rate = fields.Float(string="Total occupation rate", compute="_compute_total_occupation_rate")
    l10n_ch_is_model = fields.Selection(string="IS Model", selection=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly')
    l10n_ch_is_predefined_category = fields.Char(string="IS Predefined Category", help="Des barèmes fixes sont appliqués pour l'impôt à la source retenu sur les honoraires des administrateurs (art. 93 LIFD) et certaines participations de collaborateur (art. 97a LIFD). Pour ces impôts, aucun enfant n'est pris en compte et un seul taux en %% est appliqué. À cela s'ajoutent des catégories prédéfinies pour les annonces rectificatives et pour l'annonce des salaires bruts des frontaliers français pour lesquels l'accord spécial entre les cantons BE, BS, BL, JU, NE, SO, VD et VS et la France s'applique.")
    l10n_ch_monthly_effective_days = fields.Float(string="Monthly Effective Working Days", default=20)

    @api.depends('employee_id')
    def _compute_l10n_ch_canton(self):
        for contract in self:
            contract.l10n_ch_canton = contract.employee_id.l10n_ch_canton

    @api.depends('resource_calendar_id')
    def _compute_l10n_ch_current_occupation_rate(self):
        for contract in self:
            contract.l10n_ch_current_occupation_rate = contract.resource_calendar_id.work_time_rate

    @api.depends('l10n_ch_other_employers_occupation_rate', 'l10n_ch_current_occupation_rate', 'resource_calendar_id')
    def _compute_total_occupation_rate(self):
        for contract in self:
            contract.l10n_ch_total_occupation_rate = contract.l10n_ch_other_employers_occupation_rate + contract.l10n_ch_current_occupation_rate
