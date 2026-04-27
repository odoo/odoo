# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class L10nCHInsuranceReport(models.Model):
    _name = 'ch.yearly.report'
    _description = 'AVS / LAA / LAAC / IJM Yearly Report'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "CH":
            raise UserError(_('You must be logged in a Swiss company to use this feature'))
        return super().default_get(field_list)

    name = fields.Char(required=True)
    year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)

    avs_institution_ids = fields.Many2many('l10n.ch.social.insurance')
    laa_institution_ids = fields.Many2many('l10n.ch.accident.insurance')
    laac_institution_ids = fields.Many2many('l10n.ch.additional.accident.insurance')
    ijm_institution_ids = fields.Many2many('l10n.ch.sickness.insurance')
    caf_institution_ids = fields.Many2many('l10n.ch.compensation.fund')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    report_line_ids = fields.One2many('ch.yearly.report.line', 'report_id')

    def _get_employee_entry_withdrawals(self):
        """
        The logic is, we retrieve all contracts, if two contracts follow eachother by 1 day, we do not
        consider it a withdrawal from the company.
        """
        january_1 = date(self.year, 1, 1)
        december_31 = date(self.year, 12, 31)
        emp_contracts = self.env['hr.contract']._read_group(
            domain=[
                ('state', 'in', ['open', 'close']),
                ('company_id', '=', self.company_id.id),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'])
        aggregated_entry_withdrawals = {}
        for emp in sorted(emp_contracts, key=lambda x: x[0].name):
            periods = []
            start_end_dates = [d + relativedelta(days=-1) for d in emp[1].mapped('date_start')] + [d for d in emp[1].mapped('date_end') if d]
            if start_end_dates:
                start_end_dates = sorted(start_end_dates, reverse=True)
                current_entry = start_end_dates.pop()
                current_withdrawal = start_end_dates.pop() if start_end_dates else date(self.year, 12, 31)
                periods = []
                if start_end_dates:
                    while start_end_dates:
                        # We check the next contract start
                        next_entry = start_end_dates.pop()
                        # If they are successive contracts we extend the current period
                        if next_entry == current_withdrawal:
                            current_withdrawal = start_end_dates.pop() if start_end_dates else date(self.year, 12, 31)
                        # We have a leap in time between contracts, this is considered as a withdrawal from the company and a new entry
                        else:
                            periods.append((max(current_entry + relativedelta(days=1), january_1), min(current_withdrawal, december_31)))
                            current_entry = next_entry
                            current_withdrawal = start_end_dates.pop() if start_end_dates else date(self.year, 12, 31)
                        if not start_end_dates:
                            periods.append((max(current_entry + relativedelta(days=1), january_1), min(current_withdrawal, december_31)))
                else:
                    periods.append((max(current_entry + relativedelta(days=1), january_1), min(current_withdrawal, december_31)))
            if periods:
                aggregated_entry_withdrawals[emp[0].id] = {emp[1].filtered(lambda c: max(current_entry + relativedelta(days=1), january_1) >= p[0] and max(current_entry + relativedelta(days=1), january_1) <= p[1]): p for p in periods}
        return aggregated_entry_withdrawals

    def _get_avs_rendering_data(self, employee_moves, avs_institution):
        self.ensure_one()
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, 1, 1)),
            ('date_to', '<=', date(self.year, 12, 31)),
            ('l10n_ch_social_insurance_id', '=', avs_institution.id),
            ('l10n_ch_avs_status', 'not in', ['young', 'exempted'])
        ])
        line_values = payslips._get_line_values(['AVSSALARY', 'ACSALARY', 'ACCSALARY'], compute_sum=True)

        mapped_salaries = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
        for payslip in payslips.sudo():
            avs_salary = line_values['AVSSALARY'][payslip.id]['total']
            ac_salary = line_values['ACSALARY'][payslip.id]['total']
            acc_salary = line_values['ACCSALARY'][payslip.id]['total']
            if avs_salary or acc_salary or acc_salary:
                for contracts_per_period in employee_moves.get(payslip.employee_id.id, []):
                    if payslip.contract_id.id in contracts_per_period.ids:
                        mapped_salaries[payslip.employee_id][employee_moves[payslip.employee_id.id][contracts_per_period]][0] += avs_salary
                        mapped_salaries[payslip.employee_id][employee_moves[payslip.employee_id.id][contracts_per_period]][1] += ac_salary
                        mapped_salaries[payslip.employee_id][employee_moves[payslip.employee_id.id][contracts_per_period]][2] += acc_salary

        reporting_data = {
            'report_name': "Attestation AVS",
            'institution': avs_institution.insurance_code,
            'company': self.company_id,
            'year': self.year,
            'columns': [
                _("SV-AS Number"), _('Birthday'), _('Name'), _('From'), _('To'), _('AVS Salary'), _('AC Salary'), _('ACC Salary'), _('M/F')
            ],
            'employee_data': sorted([
                [
                    employee.l10n_ch_sv_as_number,
                    format_date(self.env, employee.birthday),
                    employee.name,
                    format_date(self.env, period[0]),
                    format_date(self.env, period[1]),
                    '%.2f %s' % (mapped_salaries[employee][period][0], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][1], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][2], self.currency_id.symbol),
                    'M' if employee.gender == 'male' else 'F'
                ] for employee in mapped_salaries for period in mapped_salaries[employee]
            ], key=lambda e: (bool(e[0]), e[2], e[3])),
            'to_monetary': lambda amount: '%.2f %s' % (amount, self.currency_id.symbol),
        }
        return reporting_data

    def _get_avs_open_rendering_data(self, employee_moves, avs_institution):
        self.ensure_one()
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, 1, 1)),
            ('date_to', '<=', date(self.year, 12, 31)),
            ('l10n_ch_social_insurance_id', '=', avs_institution.id),
        ])
        line_values = payslips._get_line_values(['AVSOPEN', 'ACOPEN'], compute_sum=True)

        mapped_salaries = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for payslip in payslips.sudo():
            avs_open = line_values['AVSOPEN'][payslip.id]['total']
            ac_open = line_values['ACOPEN'][payslip.id]['total']
            if avs_open or ac_open:
                for contracts_per_period in employee_moves.get(payslip.employee_id.id, []):
                    if payslip.contract_id.id in contracts_per_period.ids:
                        mapped_salaries[payslip.employee_id][employee_moves[payslip.employee_id.id][contracts_per_period]][0] += avs_open
                        mapped_salaries[payslip.employee_id][employee_moves[payslip.employee_id.id][contracts_per_period]][1] += ac_open

        reporting_data = {
            'report_name': "AVS Exempted Salaries",
            'institution': avs_institution.insurance_code,
            'company': self.company_id,
            'year': self.year,
            'columns': [
                _("SV-AS Number"), _('Birthday'), _('Name'), _('From'), _('To'), _('AVS Open'), _('AC Open'), _('M/F')
            ],
            'employee_data': sorted([
                [
                    employee.l10n_ch_sv_as_number,
                    format_date(self.env, employee.birthday),
                    employee.name,
                    format_date(self.env, period[0]),
                    format_date(self.env, period[1]),
                    '%.2f %s' % (mapped_salaries[employee][period][0], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][1], self.currency_id.symbol),
                    'M' if employee.gender == 'male' else 'F'
                ] for employee in mapped_salaries for period in mapped_salaries[employee]
            ], key=lambda e: (not e[0], e[2], e[3])),
            'to_monetary': lambda amount: '%.2f %s' % (amount, self.currency_id.symbol),
        }
        return reporting_data

    def _get_laa_rendering_data(self, employee_moves, laa_institution):
        self.ensure_one()
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, 1, 1)),
            ('date_to', '<=', date(self.year, 12, 31)),
            ('l10n_ch_accident_insurance_line_id', 'in', laa_institution.line_ids.ids),
        ])
        line_values = payslips._get_line_values(['GROSS', 'LAABASE', 'LAASALARY'], compute_sum=True)
        mapped_salaries = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0, False])))

        periods_per_solutions = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
        for payslip in payslips.sudo():
            periods_per_solutions[payslip.employee_id][payslip.l10n_ch_accident_insurance_line_id.solution_code] |= payslip

        for payslip in payslips.sudo():
            current_solution = payslip.l10n_ch_accident_insurance_line_id.solution_code
            gross = line_values['GROSS'][payslip.id]['total']
            laa_base = line_values['LAABASE'][payslip.id]['total']
            laa_salary = line_values['LAASALARY'][payslip.id]['total']
            if gross or laa_base or laa_salary:
                for contracts_per_period in employee_moves.get(payslip.employee_id.id, []):
                    if payslip.contract_id.id in contracts_per_period.ids:
                        current_period = employee_moves[payslip.employee_id.id][contracts_per_period]
                        ajusted_period = (max(min(periods_per_solutions[payslip.employee_id][current_solution].mapped('date_from')), current_period[0]),
                                          min(max(periods_per_solutions[payslip.employee_id][current_solution].mapped('date_to')), current_period[1]))
                        mapped_salaries[payslip.employee_id][ajusted_period][current_solution][0] += gross
                        mapped_salaries[payslip.employee_id][ajusted_period][current_solution][1] += laa_base
                        mapped_salaries[payslip.employee_id][ajusted_period][current_solution][2] += laa_salary
        reporting_data = {
            'report_name': 'LAA Statement',
            'institution': laa_institution.insurance_code,
            'company': self.company_id,
            'year': self.year,
            'columns': [
                _("Employee Number"), _('Name'), _('From'), _('To'), _('Gross Salary'), _('LAA Base'), _('LAA Salary'), _('M/F'), _('LAA Code')
            ],
            'employee_data': sorted([
                [
                    employee.id,
                    employee.name,
                    format_date(self.env, period[0]),
                    format_date(self.env, period[1]),
                    '%.2f %s' % (mapped_salaries[employee][period][solution][0], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][solution][1], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][solution][2], self.currency_id.symbol),
                    'M' if employee.gender == 'male' else 'F',
                    solution,
                ] for employee in mapped_salaries for period in mapped_salaries[employee] for solution in mapped_salaries[employee][period]
            ], key=lambda e: (e[1], e[2])),
        }
        return reporting_data

    def _get_laac_rendering_data(self, employee_moves, laac_institution):
        self.ensure_one()
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, 1, 1)),
            ('date_to', '<=', date(self.year, 12, 31)),
            ('l10n_ch_additional_accident_insurance_line_ids', 'in', laac_institution.line_ids.ids),
        ])
        line_values = payslips._get_line_values(['LAACBASE', 'LAACSALARY1', 'LAACSALARY2'], compute_sum=True)
        mapped_salaries = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, False])))

        periods_per_solutions = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
        for payslip in payslips.sudo():
            for solution in payslip.l10n_ch_additional_accident_insurance_line_ids:
                periods_per_solutions[payslip.employee_id][solution.solution_name] |= payslip

        for payslip in payslips.sudo():
            main_solution = payslip.l10n_ch_additional_accident_insurance_line_ids[0].solution_name
            second_solution = payslip.l10n_ch_additional_accident_insurance_line_ids[1].solution_name if len(payslip.l10n_ch_additional_accident_insurance_line_ids) > 1 else False
            laac_base = line_values['LAACBASE'][payslip.id]['total']
            laac_main_salary = line_values['LAACSALARY1'][payslip.id]['total']
            laac_second_salary = line_values['LAACSALARY2'][payslip.id]['total']
            if laac_base or laac_main_salary or laac_second_salary:
                for contracts_per_period in employee_moves.get(payslip.employee_id.id, []):
                    if payslip.contract_id.id in contracts_per_period.ids:
                        current_period = employee_moves[payslip.employee_id.id][contracts_per_period]
                        ajusted_period = (max(min(periods_per_solutions[payslip.employee_id][main_solution].mapped('date_from')), current_period[0]),
                                          min(max(periods_per_solutions[payslip.employee_id][main_solution].mapped('date_to')), current_period[1]))
                        mapped_salaries[payslip.employee_id][ajusted_period][main_solution][0] += laac_base
                        mapped_salaries[payslip.employee_id][ajusted_period][main_solution][1] += laac_main_salary

                        if laac_second_salary:
                            ajusted_period = (max(min(periods_per_solutions[payslip.employee_id][second_solution].mapped('date_from')), current_period[0]),
                                              min(max(periods_per_solutions[payslip.employee_id][second_solution].mapped('date_to')), current_period[1]))
                            mapped_salaries[payslip.employee_id][ajusted_period][second_solution][0] += laac_base
                            mapped_salaries[payslip.employee_id][ajusted_period][second_solution][1] += laac_second_salary

        reporting_data = {
            'report_name': 'LAAC Statement',
            'institution': laac_institution.insurance_code,
            'company': self.company_id,
            'year': self.year,
            'columns': [
                _("Employee Number"), _('Name'), _('From'), _('To'), _('LAAC Base'), _('LAAC Salary'), _('M/F'), _('LAAC Code')
            ],
            'employee_data': sorted([
                [
                    employee.id,
                    employee.name,
                    format_date(self.env, period[0]),
                    format_date(self.env, period[1]),
                    '%.2f %s' % (mapped_salaries[employee][period][solution][0], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][solution][1], self.currency_id.symbol),
                    'M' if employee.gender == 'male' else 'F',
                    solution,
                ] for employee in mapped_salaries for period in mapped_salaries[employee] for solution in mapped_salaries[employee][period]
            ], key=lambda e: (e[1], e[2])),
        }
        return reporting_data

    def _get_ijm_rendering_data(self, employee_moves, ijm_institution):
        self.ensure_one()
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, 1, 1)),
            ('date_to', '<=', date(self.year, 12, 31)),
            ('l10n_ch_sickness_insurance_line_ids', 'in', ijm_institution.line_ids.ids),
        ])
        line_values = payslips._get_line_values(['IJMBASE', 'IJMSALARY1', 'IJMSALARY2'], compute_sum=True)
        mapped_salaries = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, False])))

        periods_per_solutions = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
        for payslip in payslips.sudo():
            for solution in payslip.l10n_ch_sickness_insurance_line_ids:
                periods_per_solutions[payslip.employee_id][solution.solution_name] |= payslip

        for payslip in payslips.sudo():
            main_solution = payslip.l10n_ch_sickness_insurance_line_ids[0].solution_name
            second_solution = payslip.l10n_ch_sickness_insurance_line_ids[1].solution_name if len(payslip.l10n_ch_sickness_insurance_line_ids) > 1 else False
            ijm_base = line_values['IJMBASE'][payslip.id]['total']
            ijm_main_salary = line_values['IJMSALARY1'][payslip.id]['total']
            ijm_second_salary = line_values['IJMSALARY2'][payslip.id]['total']
            if ijm_base or ijm_main_salary or ijm_second_salary:
                for contracts_per_period in employee_moves.get(payslip.employee_id.id, []):
                    if payslip.contract_id.id in contracts_per_period.ids:
                        current_period = employee_moves[payslip.employee_id.id][contracts_per_period]
                        ajusted_period = (max(min(periods_per_solutions[payslip.employee_id][main_solution].mapped('date_from')), current_period[0]),
                                          min(max(periods_per_solutions[payslip.employee_id][main_solution].mapped('date_to')), current_period[1]))
                        mapped_salaries[payslip.employee_id][ajusted_period][main_solution][0] += ijm_base
                        mapped_salaries[payslip.employee_id][ajusted_period][main_solution][1] += ijm_main_salary

                        if ijm_second_salary:
                            ajusted_period = (max(min(periods_per_solutions[payslip.employee_id][second_solution].mapped('date_from')), current_period[0]),
                                              min(max(periods_per_solutions[payslip.employee_id][second_solution].mapped('date_to')), current_period[1]))
                            mapped_salaries[payslip.employee_id][ajusted_period][second_solution][0] += ijm_base
                            mapped_salaries[payslip.employee_id][ajusted_period][second_solution][1] += ijm_second_salary

        reporting_data = {
            'report_name': 'LAAC Statement',
            'institution': ijm_institution.insurance_code,
            'company': self.company_id,
            'year': self.year,
            'columns': [
                _("Employee Number"), _('Name'), _('From'), _('To'), _('IJM Base'), _('IJM Salary'), _('M/F'), _('IJM Code')
            ],
            'employee_data': sorted([
                [
                    employee.id,
                    employee.name,
                    format_date(self.env, period[0]),
                    format_date(self.env, period[1]),
                    '%.2f %s' % (mapped_salaries[employee][period][solution][0], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][solution][1], self.currency_id.symbol),
                    'M' if employee.gender == 'male' else 'F',
                    solution,
                ] for employee in mapped_salaries for period in mapped_salaries[employee] for solution in mapped_salaries[employee][period]
            ], key=lambda e: (e[1], e[2])),
        }
        return reporting_data

    def _get_caf_rendering_data(self, employee_moves, caf_institution):
        self.ensure_one()
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, 1, 1)),
            ('date_to', '<=', date(self.year, 12, 31)),
            ('l10n_ch_compensation_fund_id', '=', caf_institution.id),
        ])
        line_values = payslips._get_line_values(['AVSSALARY', 'CHILDALW', 'BIRTHALW'], compute_sum=True)
        mapped_salaries = defaultdict(lambda: defaultdict(lambda: [0, 0]))

        for payslip in payslips.sudo():
            avs_salary = line_values['AVSSALARY'][payslip.id]['total']
            child_alw = line_values['CHILDALW'][payslip.id]['total']
            birth_alw = line_values['BIRTHALW'][payslip.id]['total']
            if avs_salary or child_alw or birth_alw:
                for contracts_per_period in employee_moves.get(payslip.employee_id.id, []):
                    if payslip.contract_id.id in contracts_per_period.ids:
                        mapped_salaries[payslip.employee_id][employee_moves[payslip.employee_id.id][contracts_per_period]][0] += avs_salary
                        mapped_salaries[payslip.employee_id][employee_moves[payslip.employee_id.id][contracts_per_period]][1] += child_alw + birth_alw

        reporting_data = {
            'report_name': 'CAF Statement',
            'institution': caf_institution.insurance_code,
            'company': self.company_id,
            'year': self.year,
            'columns': [
                _("SV-AS Number"), _('Name'), _('From'), _('To'), _('AVS Salary'), _('Child Allowances')
            ],
            'employee_data': sorted([
                [
                    employee.l10n_ch_sv_as_number,
                    employee.name,
                    format_date(self.env, period[0]),
                    format_date(self.env, period[1]),
                    '%.2f %s' % (mapped_salaries[employee][period][0], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries[employee][period][1], self.currency_id.symbol),
                ] for employee in mapped_salaries for period in mapped_salaries[employee]
            ], key=lambda e: (e[1], e[2])),
        }
        return reporting_data

    def _get_rendering_data(self):
        employee_moves = self._get_employee_entry_withdrawals()
        return {
            'avs': [self._get_avs_rendering_data(employee_moves, avs) for avs in self.avs_institution_ids],
            'avs_open': [self._get_avs_open_rendering_data(employee_moves, avs) for avs in self.avs_institution_ids],
            'laa': [self._get_laa_rendering_data(employee_moves, laa) for laa in self.laa_institution_ids],
            'laac': [self._get_laac_rendering_data(employee_moves, laac) for laac in self.laac_institution_ids],
            'ijm': [self._get_ijm_rendering_data(employee_moves, ijm) for ijm in self.ijm_institution_ids],
            'caf': [self._get_caf_rendering_data(employee_moves, caf) for caf in self.caf_institution_ids]
        }

    def action_generate_pdf(self):
        self.ensure_one()
        rendering_data = self._get_rendering_data()
        report_vals = []
        for report_type in rendering_data:
            for institution_data in rendering_data[report_type]:
                export_insurance_pdf = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
                    self.env.ref('l10n_ch_hr_payroll.action_insurance_yearly_report'),
                    res_ids=self.ids, data=institution_data)[0]

                report_vals.append({
                        'report_type': report_type,
                        'pdf_file': base64.encodebytes(export_insurance_pdf),
                        'pdf_filename': f"{report_type}-{institution_data['institution']}-{self.year}.pdf"
                    })
        self.report_line_ids.unlink()
        self.report_line_ids = self.env['ch.yearly.report.line'].create(report_vals)

    def action_validate(self):
        self.ensure_one()


class L10nCHInsuranceReportLine(models.Model):
    _name = 'ch.yearly.report.line'
    _description = 'Insurance Reports'

    report_id = fields.Many2one('ch.yearly.report')
    report_type = fields.Selection([
        ("avs", "AVS Statement"),
        ("avs_open", "AVS Exempted Statement"),
        ("laa", "LAA Statement"),
        ("laac", "LAAC Statement"),
        ("ijm", "IJM Statement"),
        ("caf", "CAF Statement")
    ])
    pdf_file = fields.Binary(string="PDF File")
    pdf_filename = fields.Char(string="PDF Filename")
