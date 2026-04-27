# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import date
from calendar import monthrange

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round

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
    l10n_ch_after_departure_payment = fields.Selection([
        ('N', 'After Departure Payment'),
        ('NK', 'After Departure Payment with ST correction')],
        string="Code change, correction-payment after departure",
        help="Additional payment after leaving in the current year with maximum salary and third-party benefits")
    l10n_ch_lpp_not_insured = fields.Boolean(
        compute="_compute_l10n_ch_lpp_not_insured", store=True, readonly=False
    )
    l10n_ch_is_code = fields.Char(compute="_compute_l10n_ch_is_code", string="IS Code", store=True)
    l10n_ch_is_model = fields.Selection(
        string="IS Model",
        selection=[('monthly', 'Monthly'), ('yearly', 'Yearly')],
        compute="_compute_l10n_ch_is_model",
        store=True)
    l10n_ch_is_log_line_ids = fields.One2many('hr.payslip.is.log.line', 'payslip_id')
    l10n_ch_avs_status = fields.Selection([
        ('youth', 'Youth'),
        ('exempted', 'Exempted'),
        ('retired', 'Retired'),
    ], string="AVS Status", compute='_compute_l10n_ch_avs_status', store=True)
    l10n_ch_pay_13th_month = fields.Boolean(string="Pay Thirteen Month", compute="_compute_l10n_ch_pay_13th_month", store=True, readonly=False)

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

    @api.depends('payslip_run_id.l10n_ch_pay_13th_month')
    def _compute_l10n_ch_pay_13th_month(self):
        payslip_to_recompute = self.env['hr.payslip']
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done'] or not payslip.payslip_run_id:
                continue
            if payslip.l10n_ch_pay_13th_month != payslip.payslip_run_id.l10n_ch_pay_13th_month:
                if payslip.state == "waiting":
                    payslip_to_recompute += payslip
                payslip.l10n_ch_pay_13th_month = payslip.payslip_run_id.l10n_ch_pay_13th_month
        if payslip_to_recompute:
            payslip_to_recompute.compute_sheet()

    @api.depends('contract_id.l10n_ch_avs_status')
    def _compute_l10n_ch_avs_status(self):
        for payslip in self:
            contract = payslip.contract_id
            if payslip.state not in ['draft', 'verify'] or self.env.context.get('ch_skip_payslip_update'):
                continue
            payslip.l10n_ch_avs_status = contract.l10n_ch_avs_status

    @api.depends('contract_id.l10n_ch_is_model')
    def _compute_l10n_ch_is_model(self):
        for payslip in self:
            if payslip.struct_id.country_id.code != "CH":
                continue
            contract = payslip.contract_id
            if payslip.state not in ['draft', 'verify']:
                continue
            payslip.l10n_ch_is_model = contract.l10n_ch_is_model

    @api.depends('contract_id.employee_id', 'contract_id.l10n_ch_has_withholding_tax')
    def _compute_l10n_ch_is_code(self):
        for payslip in self:
            if payslip.struct_id.country_id.code != "CH":
                continue
            contract = payslip.contract_id
            if payslip.state not in ['draft', 'verify']:
                continue
            if not contract.l10n_ch_has_withholding_tax:
                payslip.l10n_ch_is_code = False
                continue

            e = contract.employee_id
            canton = e.l10n_ch_canton
            if canton == "EX":
                canton = contract.l10n_ch_location_unit_id.canton

            if contract.l10n_ch_is_predefined_category:
                payslip.l10n_ch_is_code = f"{canton}-{contract.l10n_ch_is_predefined_category}{'Y' if e.l10n_ch_church_tax else 'N'}"
            else:
                payslip.l10n_ch_is_code = f"{canton}-{e.l10n_ch_tax_scale}{int(min(e.children, 9))}{'Y' if e.l10n_ch_church_tax else 'N'}"

    @api.depends('contract_id.l10n_ch_lpp_not_insured', 'state')
    def _compute_l10n_ch_lpp_not_insured(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "CH" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_ch_lpp_not_insured = payslip.contract_id.l10n_ch_lpp_not_insured

    def _get_payslip_line_total(self, amount, quantity, rate, rule):
        total = super()._get_payslip_line_total(amount, quantity, rate, rule)
        if self.company_id.country_id.code != "CH" or not rule.l10n_ch_5_cents_rounding:
            return total
        total = float_round(total, precision_rounding=0.01, rounding_method="HALF-UP")
        if total % 0.05 >= 0.025:
            return total + 0.05 - (total % 0.05)
        return total - (total % 0.05)

    def _filter_out_of_contracts_payslips(self):
        return super()._filter_out_of_contracts_payslips().filtered(lambda p: not p.l10n_ch_after_departure_payment)

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
            payslips._compute_l10n_ch_pay_13th_month()
            payslips._compute_l10n_ch_avs_status()
            payslips._compute_l10n_ch_is_model()
            payslips._compute_l10n_ch_is_code()
            payslips._compute_l10n_ch_lpp_not_insured()
            super().action_refresh_from_work_entries()

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        if self.struct_id.code == "CHMONTHLY":
            date_from = date(self.date_from.year, 1, 1)
            date_to = self.date_from
            payslips_to_correct = self.env['hr.employee.is.line'].search([
                ('employee_id', '=', self.employee_id.id),
                ('correction_date', '>=', self.date_from),
                ('correction_date', '<', self.date_to)
            ]).payslips_to_correct

            if self.l10n_ch_after_departure_payment:
                reference_payslip = self.env['hr.payslip'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('state', 'in', ['done', 'paid']),
                    ('struct_id.code', '=', 'CHMONTHLY'),
                    ('l10n_ch_after_departure_payment', '=', False),
                ], order="date_from DESC", limit=1)
                if not reference_payslip:
                    raise ValidationError(_("A previous payslip in the system is required for after departure payement to work."))
                if reference_payslip.date_from.year != self.date_from.year:
                    date_from = date(reference_payslip.date_from.year, 1, 1)
                    date_to = self.date_from
                res.update({
                    'reference_is_slip': reference_payslip
                })
            res.update({
                'previous_payslips': self.env['hr.payslip'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('date_from', '>=', date_from),
                    ('date_to', '<', date_to),
                    ('state', 'in', ['done', 'paid']),
                    ('struct_id.code', '=', 'CHMONTHLY'),
                ]),
                'payslips_to_correct': payslips_to_correct,
            })
        return res

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

    def compute_sheet(self):
        swiss_payslips = self.filtered(lambda p: p.struct_id.code == "CHMONTHLY")
        if not swiss_payslips:
            return super().compute_sheet()
        swiss_payslips.l10n_ch_is_log_line_ids.unlink()
        result = super().compute_sheet()
        log_lines = swiss_payslips._get_is_log_lines()
        if log_lines:
            self.env['hr.payslip.is.log.line'].create(log_lines)
        return result

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

    def _get_paid_amount(self):
        self.ensure_one()
        swiss_payslip = self.struct_id.country_id.code == "CH"
        if swiss_payslip and self.struct_id.code == 'CHMONTHLY' and \
                self.input_line_ids.filtered(lambda l: l.code in ['SICKWAGE', 'ACCIDENTWAGE', 'MILITARYWAGE']):
            return 0.0
        return super()._get_paid_amount()

    def _l10n_ch_get_as_days_count(self, date_from=None, date_to=None):
        self.ensure_one()
        payslip = self
        contract = self.contract_id
        start = contract.date_start
        finish = contract.date_end

        if date_from is not None:
            start = date_from
        if date_to is not None:
            finish = date_to

        if 'FORCEASDAYS' in payslip.input_line_ids.mapped('code'):
            return payslip._get_input_line_amount('FORCEASDAYS')
        if start == finish:
            return 1
        if start == self.date_to:
            return 1
        if finish and finish == self.date_from:
            return 1
        if start > payslip.date_from and finish and finish < payslip.date_to:
            return (monthrange(payslip.date_from.year, payslip.date_from.month)[1] - ((start - payslip.date_from).days + 1) - ((payslip.date_to - finish).days)) + 1
        if start > payslip.date_from:
            return 31 - start.day
        if finish and finish < payslip.date_to and not finish < payslip.date_from:
            return finish.day
        if finish and finish < payslip.date_from:
            return 0
        return 30

    def _get_is_log_lines(self):
        line_vals = []
        rules_to_log = ['ISSALARY', 'ISDTSALARY', 'ISDTSALARYPERIODIC', 'ISDTSALARYAPERIODIC']
        for payslip in self:
            for line in payslip.line_ids:
                if line.code in rules_to_log:
                    log_line = {
                        'is_code': payslip.l10n_ch_is_code,
                        'code': line.code,
                        'amount': line.total,
                        'payslip_id': payslip.id,
                        'date': payslip.date_from
                    }
                    line_vals.append(log_line)
        return line_vals

    def _get_is_log_line_values(self):

        result = defaultdict(lambda: defaultdict(float))
        if not self:
            return result

        self.env.flush_all()
        self.env.cr.execute("""
            SELECT
                pl.is_code,
                pl.code,
                SUM(pl.amount) as total
            FROM hr_payslip_is_log_line pl
            JOIN hr_payslip p
            ON p.id IN %s
            AND ((pl.corrected_slip_id = p.id AND pl.is_correction IS TRUE) OR (pl.payslip_id = p.id AND pl.is_correction IS NOT TRUE))
            GROUP BY pl.is_code, pl.code
        """, (tuple(self.ids),))

        request_rows = self.env.cr.dictfetchall()
        result = defaultdict(lambda: defaultdict(float))
        for row in request_rows:
            is_code = row['is_code']
            result[is_code].update({
                row['code']: row['total']
            })
        return result

    def _log_is_correction(self, is_code, code, amount, corrected_payslip, is_correction=True):
        self.ensure_one()
        self.env['hr.payslip.is.log.line'].create({
            'is_code': is_code,
            'code': code,
            'amount': amount,
            'payslip_id': self.id,
            'is_correction': is_correction,
            'corrected_slip_id': corrected_payslip.id if corrected_payslip else False,
            'date': corrected_payslip.date_from if corrected_payslip else self.date_from
        })

    def _l10n_ch_find_is_rate(self, is_code, x):
        self.ensure_one()
        if not self.contract_id.l10n_ch_has_withholding_tax:
            return 0, 0
        if is_code[3:5] in ['HE', 'ME', 'NO', 'SF']:
            canton, tax_code = is_code.split("-")
            category_code = tax_code[0:2]
            church_tax = tax_code[2]
            parameter_code = f"l10n_ch_withholding_tax_rates_{canton}_{category_code}_{church_tax}"
        else:
            canton, (tax_scale, child_count, church_tax) = is_code.split("-")
            parameter_code = f"l10n_ch_withholding_tax_rates_{canton}_{church_tax}_{tax_scale}_{child_count}"
        rates = self._rule_parameter(parameter_code)

        x = float_round(x, precision_rounding=1, rounding_method='DOWN')
        for low, high, min_amount, rate in rates:
            if low <= x <= high:
                return min_amount, rate
        return 0, 0

    def action_payslip_payment_report(self, export_format='iso20022_ch'):
        action = super().action_payslip_payment_report()
        if self.company_id.country_code != 'CH':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
