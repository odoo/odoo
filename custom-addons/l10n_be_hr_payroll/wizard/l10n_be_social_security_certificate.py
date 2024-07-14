# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nBeSocialSecurityCertificate(models.TransientModel):
    _name = 'l10n.be.social.security.certificate'
    _description = 'Belgium: Social Security Certificate'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    date_from = fields.Date(default=lambda s: fields.Date.today() + relativedelta(day=1, month=1, years=-1))
    date_to = fields.Date(default=lambda s: fields.Date.today() + relativedelta(day=31, month=12, years=-1))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    social_security_sheet = fields.Binary('Social Security Certificate', readonly=True, attachment=False)
    social_security_filename = fields.Char()
    aggregation_level = fields.Selection([
        ('company', 'Whole Company'),
        ('department', 'By Department'),
        ('employee', 'By Employee')], default='company', required=True)

    def print_report(self):
        def _get_total(payslips, all_values, codes):
            return sum(all_values[code][p.id]['total'] for p in payslips for code in codes)

        self.ensure_one()

        date_from = self.date_from + relativedelta(day=1)
        date_to = self.date_to + relativedelta(day=31)

        monthly_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary')
        termination_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_termination_fees')
        holiday_pay_n = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')
        holiday_pay_n1 = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays')
        double_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday')
        thirteen_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month')
        student_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_student_regular_pay')
        warrant_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_structure_warrant')

        structures = monthly_pay + termination_pay + holiday_pay_n + holiday_pay_n1 + double_pay + thirteen_pay + student_pay

        all_payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('struct_id', '!=', warrant_pay.id),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to)])
        employees = all_payslips.mapped('employee_id')
        worker_count = len(employees)

        grouped_payslips = []
        if self.aggregation_level == 'company':
            grouped_payslips.append((self.company_id.name, all_payslips))
        elif self.aggregation_level == 'department':
            for department in all_payslips.employee_id.department_id:
                grouped_payslips.append((department.name, all_payslips.filtered(lambda p: p.employee_id.department_id == department)))
        else:
            for employee in all_payslips.employee_id:
                grouped_payslips.append((employee.name, all_payslips.filtered(lambda p: p.employee_id == employee)))

        report_data = []
        for aggregate_name, aggregate_payslips in grouped_payslips:
            monthly_slips = aggregate_payslips.filtered(lambda p: p.struct_id == monthly_pay)
            termination_slips = aggregate_payslips.filtered(lambda p: p.struct_id == termination_pay)
            holiday_slips = aggregate_payslips.filtered(lambda p: p.struct_id in [holiday_pay_n, holiday_pay_n1])
            double_slips = aggregate_payslips.filtered(lambda p: p.struct_id == double_pay)
            thirteen_slips = aggregate_payslips.filtered(lambda p: p.struct_id == thirteen_pay)
            student_slips = aggregate_payslips.filtered(lambda p: p.struct_id == student_pay)
            unclassified_slips = aggregate_payslips - monthly_slips - termination_slips - holiday_slips - double_slips - thirteen_slips - student_slips
            monthly_slips += unclassified_slips

            code_list = [
                'BASIC', 'HolPayRecN', 'HolPayRecN1', 'COMMISSION', 'AFTERPUB', 'HIRINGBONUS',
                'ADDITIONALGROSS', 'SIMPLE.DECEMBER', 'ATN.INT', 'ATN.MOB', 'ATN.LAP', 'BASIC',
                'D.P', 'EU.LEAVE.DEDUC', 'ATN.CAR', 'PAY_SIMPLE', 'PAY DOUBLE', 'PUB.TRANS',
                'PAY DOUBLE COMPLEMENTARY', 'SALARY', 'SALARY', 'ONSSTOTAL', 'ONSSEMPLOYER', 'ONSS1',
                'ONSS2', 'ONSS', 'ONSS', 'ONSS', 'REP.FEES', 'REP.FEES.VOLATILE', 'CAR.PRIV', 'P.P', 'M.ONSS',
                'ATTACH_SALARY', 'ATN.CAR.2', 'ATN.MOB.2', 'ATN.INT.2', 'ATN.LAP.2', 'MEAL_V_EMP',
                'IMPULSION25', 'IMPULSION12', 'ASSIG_SALARY', 'ADVANCE', 'NET', 'P.P.DED',
                'ONSSEMPLOYERBASIC', 'ONSSEMPLOYERFFE', 'ONSSEMPLOYERMFFE', 'ONSSEMPLOYERCPAE',
                'ONSSEMPLOYERRESTREINT', 'ONSSEMPLOYERUNEMP', 'CYCLE', 'CANTEEN']
            all_values = aggregate_payslips._get_line_values(code_list, vals_list=['total', 'quantity'])

            gross_before_onss = _get_total(monthly_slips, all_values, [
                'BASIC', 'HolPayRecN', 'HolPayRecN1', 'COMMISSION', 'AFTERPUB', 'HIRINGBONUS',
                'ADDITIONALGROSS', 'SIMPLE.DECEMBER'])
            atn = _get_total(monthly_slips, all_values, ['ATN.INT', 'ATN.MOB', 'ATN.LAP'])
            termination_fees = _get_total(termination_slips, all_values, ['BASIC'])
            student = _get_total(student_slips, all_values, ['BASIC'])
            thirteen_month = _get_total(thirteen_slips, all_values, ['BASIC'])
            double_pay = _get_total(double_slips, all_values, ['D.P', 'EU.LEAVE.DEDUC'])
            total_gross_before_onss = gross_before_onss + atn + termination_fees + student + thirteen_month + double_pay
            atn_without_onss = _get_total(monthly_slips, all_values, ['ATN.CAR'])
            early_holiday_pay = _get_total(holiday_slips, all_values, ['PAY_SIMPLE'])
            holiday_pay_supplement = _get_total(holiday_slips, all_values, ['PAY DOUBLE'])
            other_exempted_amount = _get_total(holiday_slips, all_values, ['PAY DOUBLE COMPLEMENTARY'])
            thirteen_month_gross = _get_total(thirteen_slips, all_values, ['SALARY'])
            double_gross = _get_total(double_slips, all_values, ['SALARY'])
            subtotal_gross = total_gross_before_onss + atn_without_onss + early_holiday_pay + holiday_pay_supplement + other_exempted_amount + double_gross
            onss_cotisation = _get_total(monthly_slips, all_values, ['ONSSTOTAL'])
            onss_cotisation_termination_fees = _get_total(termination_slips, all_values, ['ONSSTOTAL'])
            anticipated_holiday_pay_retenue = _get_total(holiday_slips, all_values, ['ONSS1'])
            holiday_pay_supplement_retenue = _get_total(holiday_slips, all_values, ['ONSS2'])
            onss_thirteen_month = _get_total(thirteen_slips, all_values, ['ONSS'])
            onss_double = _get_total(double_slips, all_values, ['ONSS'])
            onss_student = _get_total(student_slips, all_values, ['ONSS'])
            representation_fees = _get_total(monthly_slips, all_values, ['REP.FEES', 'REP.FEES.VOLATILE'])
            private_car = _get_total(monthly_slips + student_slips, all_values, ['CAR.PRIV'])
            public_transport = _get_total(monthly_slips + student_slips, all_values, ['PUB.TRANS'])
            cycle_allowance = _get_total(monthly_slips + student_slips, all_values, ['CYCLE'])
            canteen_costs = _get_total(monthly_slips, all_values, ['CANTEEN'])
            atn_car = atn_without_onss
            withholding_taxes = _get_total(aggregate_payslips, all_values, ['P.P'])
            misc_onss = _get_total(aggregate_payslips, all_values, ['M.ONSS'])
            salary_attachment = _get_total(aggregate_payslips, all_values, ['ATTACH_SALARY'])
            atn_deduction = _get_total(monthly_slips, all_values, ['ATN.CAR.2', 'ATN.MOB.2', 'ATN.INT.2', 'ATN.LAP.2'])
            meal_voucher_employee = _get_total(monthly_slips + student_slips, all_values, ['MEAL_V_EMP'])
            net_third_party = _get_total(monthly_slips, all_values, ['IMPULSION25', 'IMPULSION12'])
            salary_assignment = _get_total(aggregate_payslips, all_values, ['ASSIG_SALARY'])
            salary_advance = _get_total(monthly_slips, all_values, ['ADVANCE'])
            net = _get_total(aggregate_payslips, all_values, ['NET'])
            total_net = net + salary_advance

            # Cotisation patronnale de base =
            # Global Rate (without employee part) + FFE + Special FFE + CPAE + Modération Salariale + Chomage temporaire
            # global_rate = 0.3810 + 0.0023 + (0.0169 if worker_count >= 10 else 0) + 0.0010 - 0.1307
            emp_onss = _get_total(monthly_slips + thirteen_slips + holiday_slips, all_values, ['ONSSEMPLOYER'])
            emp_termination_onss = _get_total(termination_slips, all_values, ['ONSSEMPLOYER'])
            closure_fund = _get_total(termination_slips + monthly_slips + thirteen_slips + holiday_slips, all_values, ['ONSSEMPLOYERFFE', 'ONSSEMPLOYERMFFE'])
            charges_redistribution = 0

            if 'vehicle_id' in self.env['hr.payslip']:
                co2_fees = sum(p.vehicle_id.with_context(co2_fee_date=p.date_from)._get_co2_fee(p.vehicle_id.co2, p.vehicle_id.fuel_type) for p in monthly_slips)
            else:
                co2_fees = 0
            structural_reductions = 0
            meal_voucher_employer = sum(all_values['MEAL_V_EMP'][p.id]['quantity'] * p.contract_id.meal_voucher_paid_by_employer for p in monthly_slips + student_slips)
            withholding_taxes_deduction = _get_total(monthly_slips, all_values, ['P.P.DED'])
            total_employer_cost = emp_onss + emp_termination_onss + closure_fund + charges_redistribution + co2_fees + structural_reductions + meal_voucher_employer + withholding_taxes_deduction
            holiday_pay_provision = 0

            wizard_274 = self.env['l10n_be.274_xx'].new({
                'date_start': date_from,
                'date_end': date_to,
            })
            if self.aggregation_level in ['department', 'employee']:
                employee_ids = aggregate_payslips.employee_id.ids
                wizard_274.with_context(wizard_274xx_force_employee_ids=employee_ids)._compute_line_ids()

            withholding_taxes_exemption_32 = wizard_274.deducted_amount_32
            withholding_taxes_exemption_33 = wizard_274.deducted_amount_33
            withholding_taxes_exemption_34 = wizard_274.deducted_amount_34
            withholding_taxes_capping = -wizard_274.capped_amount_34

            aggregate_data = {
                'gross_before_onss': gross_before_onss,
                'atn': atn,
                'termination_fees': termination_fees,
                'student': student,
                'thirteen_month': thirteen_month,
                'double_pay': double_pay,
                'total_gross_before_onss': total_gross_before_onss,
                'atn_without_onss': atn_without_onss,
                'early_holiday_pay': early_holiday_pay,
                'holiday_pay_supplement': holiday_pay_supplement,
                'other_exempted_amount': other_exempted_amount,
                'thirteen_month_gross': thirteen_month_gross,
                'double_gross': double_gross,
                'subtotal_gross': subtotal_gross,
                'onss_cotisation': onss_cotisation,
                'onss_cotisation_termination_fees': onss_cotisation_termination_fees,
                'anticipated_holiday_pay_retenue': anticipated_holiday_pay_retenue,
                'holiday_pay_supplement_retenue': holiday_pay_supplement_retenue,
                'onss_student': onss_student,
                'onss_thirteen_month': onss_thirteen_month,
                'onss_double': onss_double,
                'taxable_adaptation': 0,
                'taxable_325': 0,
                'gift_in_kind': 0,
                'representation_fees': representation_fees,
                'private_car': private_car,
                'public_transport': public_transport,
                'cycle_allowance': cycle_allowance,
                'atn_car': atn_car,
                'canteen_costs': canteen_costs,
                'withholding_taxes': withholding_taxes,
                'misc_onss': misc_onss,
                'salary_attachment': salary_attachment,
                'atn_deduction': atn_deduction,
                'meal_voucher_employee': meal_voucher_employee,
                'net_third_party': net_third_party,
                'salary_assignment': salary_assignment,
                'salary_advance': salary_advance,
                'net': net,
                'total_net': total_net,
                'emp_onss': emp_onss,
                'emp_termination_onss': emp_termination_onss,
                'closure_fund': closure_fund,
                'charges_redistribution': charges_redistribution,
                'co2_fees': co2_fees,
                'structural_reductions': structural_reductions,
                'meal_voucher_employer': meal_voucher_employer,
                'withholding_taxes_deduction': withholding_taxes_deduction,
                'total_employer_cost': total_employer_cost,
                'holiday_pay_provision': holiday_pay_provision,
                'withholding_taxes_exemption_32': withholding_taxes_exemption_32,
                'withholding_taxes_exemption_33': withholding_taxes_exemption_33,
                'withholding_taxes_exemption_34': withholding_taxes_exemption_34,
                'withholding_taxes_capping': withholding_taxes_capping,
            }
            report_data.append((aggregate_name, aggregate_data))

        filename = 'SocialBalance-%s-%s.pdf' % (self.date_from.strftime("%d%B%Y"), self.date_to.strftime("%d%B%Y"))
        export_274_sheet_pdf, dummy = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            self.env.ref('l10n_be_hr_payroll.action_report_social_security_certificate').id,
            res_ids=self.ids, data={'report_data': report_data})

        self.social_security_filename = filename
        self.social_security_sheet = base64.encodebytes(export_274_sheet_pdf)

        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_validate(self):
        self.ensure_one()
        if self.social_security_sheet:
            self._post_process_generated_file(self.social_security_sheet, self.social_security_filename)
        return {'type': 'ir.actions.act_window_close'}

    # To be overwritten in documents_l10n_be_hr_payroll to create a document.document
    def _post_process_generated_file(self, data, filename):
        return
