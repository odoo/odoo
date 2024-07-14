# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

SWISS_LANGUAGES = ["it_IT", "de_DE", "de_CH", "fr_FR", "fr_CH", "en_EN", "en_US"]


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_ch_social_insurance_id = fields.Many2one(
        'l10n.ch.social.insurance', string="AVS/AC Insurance",
        compute="_compute_l10n_ch_social_insurance_id", store=True, readonly=False)
    l10n_ch_lpp_insurance_id = fields.Many2one(
        'l10n.ch.lpp.insurance', string="LPP Insurance",
        compute="_compute_l10n_ch_lpp_insurance_id", store=True, readonly=False)
    l10n_ch_accident_insurance_line_id = fields.Many2one(
        'l10n.ch.accident.insurance.line', string="AAP/AANP Insurance",
        compute="_compute_l10n_ch_accident_insurance_line_id", store=True, readonly=False)
    l10n_ch_additional_accident_insurance_line_ids = fields.Many2many(
        'l10n.ch.additional.accident.insurance.line', string="LAAC Insurances",
        compute="_compute_l10n_ch_additional_accident_insurance_line_ids", store=True, readonly=False)
    l10n_ch_sickness_insurance_line_ids = fields.Many2many(
        'l10n.ch.sickness.insurance.line', string="IJM Insurances",
        compute="_compute_l10n_ch_sickness_insurance_line_ids", store=True, readonly=False)
    l10n_ch_compensation_fund_id = fields.Many2one(
        'l10n.ch.compensation.fund', string="Family Allowance (CAF)",
        compute="_compute_l10n_ch_compensation_fund_id", store=True, readonly=False)

    @api.depends('contract_id.l10n_ch_social_insurance_id', 'state')
    def _compute_l10n_ch_social_insurance_id(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_ch_social_insurance_id = payslip.contract_id.l10n_ch_social_insurance_id

    @api.depends('contract_id.l10n_ch_lpp_insurance_id', 'state')
    def _compute_l10n_ch_lpp_insurance_id(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_ch_lpp_insurance_id = payslip.contract_id.l10n_ch_lpp_insurance_id

    @api.depends('contract_id.l10n_ch_accident_insurance_line_id', 'state')
    def _compute_l10n_ch_accident_insurance_line_id(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_ch_accident_insurance_line_id = payslip.contract_id.l10n_ch_accident_insurance_line_id

    @api.depends('contract_id.l10n_ch_additional_accident_insurance_line_ids', 'state')
    def _compute_l10n_ch_additional_accident_insurance_line_ids(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_ch_additional_accident_insurance_line_ids = [(6, 0, payslip.contract_id.l10n_ch_additional_accident_insurance_line_ids.ids)]

    @api.depends('contract_id.l10n_ch_sickness_insurance_line_ids', 'state')
    def _compute_l10n_ch_sickness_insurance_line_ids(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_ch_sickness_insurance_line_ids = [(6, 0, payslip.contract_id.l10n_ch_sickness_insurance_line_ids.ids)]

    @api.depends('contract_id.l10n_ch_compensation_fund_id', 'state')
    def _compute_l10n_ch_compensation_fund_id(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_ch_compensation_fund_id = payslip.contract_id.l10n_ch_compensation_fund_id

    def action_refresh_from_work_entries(self):
        if any(p.state not in ['draft', 'verify'] for p in self):
            super().action_refresh_from_work_entries()
        else:
            payslips = self.filtered(lambda p: p.struct_id.country_id.code == "CH")
            payslips.mapped('input_line_ids').unlink()
            payslips._compute_input_line_ids()
            payslips._compute_l10n_ch_social_insurance_id()
            payslips._compute_l10n_ch_lpp_insurance_id()
            payslips._compute_l10n_ch_accident_insurance_line_id()
            payslips._compute_l10n_ch_additional_accident_insurance_line_ids()
            payslips._compute_l10n_ch_sickness_insurance_line_ids()
            payslips._compute_l10n_ch_compensation_fund_id()
            super().action_refresh_from_work_entries()

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        if self.struct_id.code == "CHMONTHLY":
            res.update({
                'previous_payslips': self.env['hr.payslip'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('date_from', '>=', date(self.date_from.year, 1, 1)),
                    ('date_to', '<', self.date_from),
                    ('state', 'in', ['done', 'paid']),
                    ('struct_id.code', '=', 'CHMONTHLY'),
                ])
            })
        return res

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_ch_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/hr_salary_rule_data.xml',
            ])]

    def _is_invalid(self):
        invalid = super()._is_invalid()
        if not invalid and self._is_active_swiss_languages():
            country = self.struct_id.country_id
            lang_employee = self.employee_id.lang
            if country.code == 'CH' and lang_employee not in SWISS_LANGUAGES:
                return _('This document is a translation. This is not a legal document.')
        return invalid

    def _is_active_swiss_languages(self):
        active_langs = self.env['res.lang'].with_context(active_test=True).search([]).mapped('code')
        return any(l in active_langs for l in SWISS_LANGUAGES)

    def action_payslip_done(self):
        if self._is_active_swiss_languages():
            bad_language_slips = self.filtered(
                lambda p: p.struct_id.country_id.code == "CH" and p.employee_id.lang not in SWISS_LANGUAGES)
            if bad_language_slips:
                action = self.env['ir.actions.act_window'].\
                    _for_xml_id('l10n_ch_hr_payroll.l10n_ch_hr_payroll_employee_lang_wizard_action')
                ctx = dict(self.env.context)
                ctx.update({
                    'employee_ids': bad_language_slips.employee_id.ids,
                    'default_slip_ids': self.ids,
                })
                action['context'] = ctx
                return action
        return super().action_payslip_done()

    def compute_sheet(self):
        swiss_payslips = self.filtered(lambda p: p.struct_id.country_id.code == "CH")
        swiss_employees = swiss_payslips.employee_id
        invalid_employees = swiss_employees.filtered(lambda e: not e.l10n_ch_canton)
        if invalid_employees:
            raise UserError(_('No specified canton for employees:\n%s', '\n'.join(invalid_employees.mapped('name'))))

        invalid_employees = swiss_employees.filtered(lambda e: e.l10n_ch_has_withholding_tax and not e.l10n_ch_tax_scale)
        if invalid_employees:
            raise UserError(_('No specified tax scale for foreign employees:\n%s', '\n'.join(invalid_employees.mapped('name'))))

        return super().compute_sheet()

    def _get_paid_amount(self):
        self.ensure_one()
        swiss_payslip = self.struct_id.country_id.code == "CH"
        if swiss_payslip and self.struct_id.code == 'CHMONTHLY' and \
                self.input_line_ids.filtered(lambda l: l.code in ['SICKWAGE', 'ACCIDENTWAGE', 'MILITARYWAGE']):
            return 0.0
        return super()._get_paid_amount()
