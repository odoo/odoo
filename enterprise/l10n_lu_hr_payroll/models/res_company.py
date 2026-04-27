# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_lu_official_social_security = fields.Char(string="Official Social Security")
    l10n_lu_seculine = fields.Char(string="SECUline Number")

    l10n_lu_accident_insurance_factor = fields.Selection(
        selection=[
            ('0.9', '0.9'),
            ('1.0', '1.0'),
            ('1.1', '1.1'),
            ('1.3', '1.3'),
            ('1.5', '1.5')],
        default="1.0",
        string="Accident Insurance Factor",
        required=True)
    l10n_lu_accident_insurance_rate = fields.Float(
        string="Accident Insurance Rate", compute='_compute_l10n_lu_accident_insurance_rate')

    l10n_lu_mutuality_class = fields.Selection(
        selection=[
            ('1', "1 (Financial Absenteeism Rate < 0.65%)"),
            ('2', "2 (Financial Absenteeism Rate < 1.60%)"),
            ('3', "3 (Financial Absenteeism Rate < 2.50%)"),
            ('4', "4 (Financial Absenteeism Rate > 2.50%)")],
        default='1',
        string="Mutuality Class",
        required=True)
    l10n_lu_mutuality_rate = fields.Float(
        string="Mutuality Rate", compute='_compute_l10n_lu_mutuality_rate')

    @api.depends('l10n_lu_accident_insurance_factor')
    def _compute_l10n_lu_accident_insurance_rate(self):
        rate = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_accident_insurance_rate', raise_if_not_found=False) or 0.7
        for company in self:
            company.l10n_lu_accident_insurance_rate = float(company.l10n_lu_accident_insurance_factor) * rate

    @api.depends('l10n_lu_mutuality_class')
    def _compute_l10n_lu_mutuality_rate(self):
        rates = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_mutuality_rates', raise_if_not_found=False) or (0.72, 1.22, 1.76, 2.84)
        for company in self:
            company.l10n_lu_mutuality_rate = rates[int(company.l10n_lu_mutuality_class) - 1]
