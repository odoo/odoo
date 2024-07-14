# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
        'l10n.ch.accident.insurance.line', string="AAP/AANP Insurance")
    l10n_ch_additional_accident_insurance_line_ids = fields.Many2many(
        'l10n.ch.additional.accident.insurance.line', string="LAAC Insurances")
    l10n_ch_sickness_insurance_line_ids = fields.Many2many(
        'l10n.ch.sickness.insurance.line', string="IJM Insurances")
    l10n_ch_compensation_fund_id = fields.Many2one(
        'l10n.ch.compensation.fund', string="Family Allowance (CAF)")
