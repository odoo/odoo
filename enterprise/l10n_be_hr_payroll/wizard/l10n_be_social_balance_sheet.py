# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import collections
import logging

from io import BytesIO
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter, format_date, format_time

_logger = logging.getLogger(__name__)


class L10nBeSocialBalanceSheet(models.TransientModel):
    _name = 'l10n.be.social.balance.sheet'
    _description = 'Belgium: Social Balance Sheet'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    # Source: https://www.nbb.be/fr/centrale-des-bilans/etablir/modeles-des-comptes-annuels/bilan-social
    # Introduction: https://www.nbb.be/doc/ba/socialbalance/avis_cnc_2009_12.pdf
    # Q&A about social balance sheet: https://www.nbb.be/doc/ba/socialbalance/avis_cnc_s100.pdf
    # Explanations about trainings: https://www.nbb.be/doc/ba/socialbalance/avis_cnc_2009_12.pdf
    # Blank complete scheme example: https://www.nbb.be/doc/ba/socialbalance/models/bilan_social_c_20121201.pdf

    date_from = fields.Date(default=lambda s: fields.Date.today() + relativedelta(day=1, month=1, years=-1))
    date_to = fields.Date(default=lambda s: fields.Date.today() + relativedelta(day=31, month=12, years=-1))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
    state_xlsx = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    social_balance_sheet = fields.Binary('Social Balance Sheet', readonly=True, attachment=False)
    social_balance_filename = fields.Char()
    social_balance_xlsx = fields.Binary('Social Balance Sheet Spreadsheet', readonly=True, attachment=False)
    social_balance_filename_xlsx = fields.Char()

    def _get_report_data(self):
        self.ensure_one()
        number_of_months_period = (self.date_to.year - self.date_from.year) * 12 + self.date_to.month - self.date_from.month + 1
        contracts = self.env['hr.employee']._get_all_contracts(self.date_from, self.date_to, states=['open', 'close'])
        invalid_employees = contracts.employee_id.filtered(lambda e: e.gender not in ['male', 'female'])
        if invalid_employees:
            raise UserError(_('Please configure a gender (either male or female) for the following employees:\n\n%s', '\n'.join(invalid_employees.mapped('name'))))

        reports_data = {}
        max_int_len = len(str(number_of_months_period + 1))
        for i in range(number_of_months_period + 1):
            if i == number_of_months_period:
                date_from = self.date_from
                date_to = self.date_to
            else:
                date_from = self.date_from + relativedelta(day=1, months=i % 12, years=i // 12)
                date_to = date_from + relativedelta(day=31)
            report_data = {}
            cip = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cip')

            payslips = self.env['hr.payslip'].search([
                ('state', 'in', ['done', 'paid']),
                ('struct_id.type_id', '=', self.env.ref('hr_contract.structure_type_employee_cp200').id),
                ('company_id', '=', self.company_id.id),
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
                ('contract_id.contract_type_id', '!=', cip.id)])

            # SECTION 100
            # Calculated as the average of number of workers entered in the personnel register at
            # the end of each month of the accounting year.

            # 2 payslips on different working rate on the same month should be treated
            # specifically
            mapped_payslips = collections.defaultdict(lambda: self.env['hr.payslip'])
            for payslip in payslips:
                period = (payslip.date_from.month, payslip.date_from.year, payslip.employee_id.id)
                mapped_payslips[period] |= payslip

            workers_data = collections.defaultdict(lambda: dict(full=0, part=0, fte=0))

            for period, employee_payslips in mapped_payslips.items():
                if len(employee_payslips) > 1:
                    # What matters is the occupation at the end of the month. Take the most recent contract
                    payslip = employee_payslips.sorted(lambda p: p.contract_id.date_start, reverse=True)[-1]
                else:
                    payslip = employee_payslips
                gender = payslip.employee_id.gender
                calendar = payslip.contract_id.resource_calendar_id
                if calendar.full_time_required_hours == calendar.hours_per_week:
                    workers_data[gender]['full'] += 1
                    workers_data[gender]['fte'] += 1
                else:
                    workers_data[gender]['part'] += 1
                    workers_data[gender]['fte'] += 1 * calendar.work_time_rate / 100.0

            report_data.update({
                '1001_male': round(workers_data['male']['full'] / 12.0, 2),
                '1001_female': round(workers_data['female']['full'] / 12.0, 2),
                '1001_total': round((workers_data['male']['full'] + workers_data['female']['full']) / 12.0, 2),
                '1002_male': round(workers_data['male']['part'] / 12.0, 2),
                '1002_female': round(workers_data['female']['part'] / 12.0, 2),
                '1002_total': round((workers_data['male']['part'] + workers_data['female']['part']) / 12.0, 2),
                '1003_male': round(workers_data['male']['fte'] / 12.0, 2),
                '1003_female': round(workers_data['female']['fte'] / 12.0, 2),
                '1003_total': round((workers_data['male']['fte'] + workers_data['female']['fte']) / 12.0, 2),
            })

            # SECTION 101
            # The methodological notice concerning the social report published in the Belgian Official
            # Gazette (Moniteur belge) of August 30, 1996 specifies that the actual number of hours
            # worked (item 101) includes: "the total hours actually worked performed and paid during
            # the year; that is to say without take into account unpaid overtime (62), vacation, sick
            # leave, absences of short duration (63) and hours lost due to strike or for any other
            # reason ”.
            # This definition is directly followed by the description of what is meant by number of
            # hours worked on the basis of the quarterly declaration to the ONSS. This way to proceed
            # may lead to an overestimation of the hours of work actually performed. Indeed, the
            # ONSS takes into account the hours or days not worked but assimilated (64) to working days
            # to determine the employee benefits.
            attendances = self.env.ref('hr_work_entry.work_entry_type_attendance') \
                        + self.env.ref('l10n_be_hr_payroll.work_entry_type_training') \
                        + self.env.ref('l10n_be_hr_payroll.work_entry_type_additional_paid')
            workers_data = collections.defaultdict(lambda: dict(full=0, part=0, fte=0))

            for payslip in payslips:
                gender = payslip.employee_id.gender
                lines = payslip.worked_days_line_ids.filtered(lambda l: l.work_entry_type_id in attendances)
                if lines:
                    worked_paid_hours = sum(l.number_of_hours for l in lines)
                else:
                    continue
                calendar = payslip.contract_id.resource_calendar_id
                if calendar.full_time_required_hours == calendar.hours_per_week:
                    workers_data[gender]['full'] += worked_paid_hours
                    workers_data[gender]['fte'] += worked_paid_hours
                else:
                    workers_data[gender]['part'] += worked_paid_hours
                    workers_data[gender]['fte'] += worked_paid_hours
            report_data.update({
                '1011_male': round(workers_data['male']['full'], 2),
                '1011_female': round(workers_data['female']['full'], 2),
                '1011_total': round((workers_data['male']['full'] + workers_data['female']['full']), 2),
                '1012_male': round(workers_data['male']['part'], 2),
                '1012_female': round(workers_data['female']['part'], 2),
                '1012_total': round((workers_data['male']['part'] + workers_data['female']['part']), 2),
                '1013_male': round(workers_data['male']['fte'], 2),
                '1013_female': round(workers_data['female']['fte'], 2),
                '1013_total': round((workers_data['male']['fte'] + workers_data['female']['fte']), 2),
            })

            # SECTION 102 - 103: Staff Costs
            # Must be mentioned under heading 102 - "Expenses of personnel" charges which by reason of
            # their nature are entered under heading 62 of the minimum chart of accounts standardized,
            # provided that these loads concern workers covered by the social report (see above). Are
            # therefore included under the above heading, in so far as they concern the workers in
            # question:
            # - direct compensation and social benefits;
            # - employer's social contributions;
            # - employer premiums for extra-legal insurance;
            # - other personnel costs.
            workers_data = collections.defaultdict(lambda: collections.defaultdict(lambda: dict(full=0, part=0)))
            meal_voucher = dict(male=0, female=0, total=0)

            line_values = payslips._get_line_values(
                ['GROSS', 'CAR.PRIV', 'ONSSEMPLOYER', 'MEAL_V_EMP', 'PUB.TRANS', 'REP.FEES', 'IP.PART'], vals_list=['total', 'quantity'])
            for payslip in payslips:
                gender = payslip.employee_id.gender
                if gender not in ['male', 'female']:
                    raise UserError(_('Please configure a gender (either male or female) for the following employee: %s', payslip.employee_id.name))
                calendar = payslip.contract_id.resource_calendar_id
                contract_type = 'full' if calendar.full_time_required_hours == calendar.hours_per_week else 'part'
                gross = round(line_values['GROSS'][payslip.id]['total'], 2) - round(line_values['IP.PART'][payslip.id]['total'], 2)
                private_car = round(line_values['CAR.PRIV'][payslip.id]['total'], 2)
                public_transport = round(line_values['PUB.TRANS'][payslip.id]['total'], 2)
                onss_employer = round(line_values['ONSSEMPLOYER'][payslip.id]['total'], 2)
                reimbursed_expenses = round(line_values['REP.FEES'][payslip.id]['total'], 2)
                workers_data['total_gross'][gender][contract_type] += gross
                workers_data['private_car'][gender][contract_type] += private_car
                workers_data['public_transport'][gender][contract_type] += public_transport
                workers_data['onss_employer'][gender][contract_type] += onss_employer
                workers_data['reimbursed_expenses'][gender][contract_type] += reimbursed_expenses
                workers_data['total'][gender][contract_type] += gross + private_car + onss_employer + public_transport + reimbursed_expenses

                employer_amount = payslip.contract_id.meal_voucher_paid_by_employer
                meal_voucher[gender] += round(employer_amount * line_values['MEAL_V_EMP'][payslip.id]['quantity'], 2)

            report_data['102'] = workers_data
            report_data['103'] = meal_voucher

            # SECTION 105-113, 120, 121, 130-134: At the end of the exercice
            workers_data = collections.defaultdict(lambda: dict(full=0, part=0, fte=0))

            end_contracts = self.env['hr.employee']._get_all_contracts(self.date_to, self.date_to, states=['open', 'close'])
            end_contracts = end_contracts.filtered(lambda c: c.contract_type_id != cip)

            cdi = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdi')
            cdd = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdd')
            replacement = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_replacement')
            defined_work = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_clearly_defined_work')
            mapped_types = {
                cdi: '110',
                cdd: '111',
                defined_work: '112',
                replacement: '113',
            }

            mapped_certificates = {
                ('male', 'graduate'): '1202',
                ('male', 'bachelor'): '1202',
                ('male', 'master'): '1203',
                ('male', 'doctor'): '1203',
                ('male', 'other'): '1201',
                ('male', 'civil_engineer'): '1203',
                ('female', 'graduate'): '1212',
                ('female', 'bachelor'): '1212',
                ('female', 'master'): '1213',
                ('female', 'doctor'): '1213',
                ('female', 'other'): '1211',
                ('female', 'civil_engineer'): '1213',
            }

            cp200_employees = self.env.ref('hr_contract.structure_type_employee_cp200')
            cp200_students = self.env.ref('l10n_be_hr_payroll.structure_type_student')
            mapped_categories = {
                cp200_employees: '134',
                cp200_students: '133',
            }

            for contract in end_contracts:
                if contract.contract_type_id not in mapped_types:
                    _logger.info(_("The contract %(contract_name)s for %(employee)s is not of one the following types: CDI, CDD. Replacement, For a clearly defined work", contract_name=contract.name, employee=contract.employee_id.name))
                    continue
                structure_type = contract.structure_type_id
                if cip and contract.contract_type_id == cip:
                    # CIP Contracts are considered as trainees
                    structure_type = cp200_students
                if structure_type not in mapped_categories:
                    _logger.info(_("The contract %(contract_name)s for %(employee)s is not of one the following types: CP200 Employees or Student", contract_name=contract.name, employee=contract.employee_id.name))
                    continue

                gender = contract.employee_id.gender
                calendar = contract.resource_calendar_id
                contract_time = 'full' if calendar.full_time_required_hours == calendar.hours_per_week else 'part'

                workers_data['105'][contract_time] += 1
                workers_data['105']['fte'] += 1 * calendar.work_time_rate / 100.0

                contract_type = mapped_types[contract.contract_type_id]
                workers_data[contract_type][contract_time] += 1
                workers_data[contract_type]['fte'] += 1 * calendar.work_time_rate / 100.0

                if (gender, contract.employee_id.certificate) not in mapped_certificates:
                    raise UserError(_("The employee %s doesn't have a specified certificate", contract.employee_id.name))
                gender_code = '120' if gender == 'male' else '121'
                workers_data[gender_code][contract_time] += 1
                workers_data[gender_code]['fte'] += 1 * calendar.work_time_rate / 100.0
                gender_certificate_code = mapped_certificates[(gender, contract.employee_id.certificate)]
                workers_data[gender_certificate_code][contract_time] += 1
                workers_data[gender_certificate_code]['fte'] += 1 * calendar.work_time_rate / 100.0

                category_code = mapped_categories[structure_type]
                workers_data[category_code][contract_time] += 1
                workers_data[category_code]['fte'] += 1 * calendar.work_time_rate / 100.0

            for code in [
                    '105', '110', '111', '112', '113',
                    '120', '1200', '1201', '1202', '1203',
                    '121', '1210', '1211', '1212', '1213',
                    '130', '132', '133', '134']:
                report_data[code] = workers_data[code]

            # SECTION 200: Staff Movements (Entries / Departure)
            workers_data = collections.defaultdict(lambda: dict(full=0, part=0, fte=0))

            in_mapped_types = {
                cdi: '210',
                cdd: '211',
                defined_work: '212',
                replacement: '213',
            }
            out_mapped_types = {
                cdi: '310',
                cdd: '311',
                defined_work: '312',
                replacement: '313',
            }

            in_employees = self.env['hr.employee']
            out_employees = self.env['hr.employee']
            for period, employee_payslips in mapped_payslips.items():
                if len(employee_payslips) > 1:
                    # What matters is the occupation at the end of the month. Take the most recent contract
                    payslip = employee_payslips.sorted(lambda p: p.contract_id.date_start, reverse=True)[-1]
                else:
                    payslip = employee_payslips
                employee = payslip.employee_id
                contract = payslip.contract_id
                gender = payslip.employee_id.gender
                if contract.contract_type_id not in in_mapped_types:
                    _logger.info(_("The contract %(contract_name)s for %(employee)s is not of one the following types: CDI, CDD. Replacement, For a clearly defined work", contract_name=contract.name, employee=contract.employee_id.name))
                    continue
                calendar = contract.resource_calendar_id
                contract_time = 'full' if calendar.full_time_required_hours == calendar.hours_per_week else 'part'
                if employee not in in_employees and employee.first_contract_date and (date_from <= employee.first_contract_date <= date_to):
                    in_employees |= employee

                    workers_data['205'][contract_time] += 1
                    workers_data['205']['fte'] += 1 * calendar.work_time_rate / 100.0

                    contract_type = in_mapped_types[contract.contract_type_id]
                    workers_data[contract_type][contract_time] += 1
                    workers_data[contract_type]['fte'] += 1 * calendar.work_time_rate / 100.0
                departure_date = employee.end_notice_period or employee.departure_date
                if departure_date and employee not in out_employees and (date_from <= departure_date <= date_to):
                    out_employees |= employee

                    workers_data['305'][contract_time] += 1
                    workers_data['305']['fte'] += 1 * calendar.work_time_rate / 100.0

                    contract_type = out_mapped_types[contract.contract_type_id]
                    workers_data[contract_type][contract_time] += 1
                    workers_data[contract_type]['fte'] += 1 * calendar.work_time_rate / 100.0

                    reason_code = employee.departure_reason_id.reason_code
                    reason_code = str(reason_code if reason_code in [340, 341, 342, 343] else 343)
                    workers_data[reason_code][contract_time] += 1
                    workers_data[reason_code]['fte'] += 1 * calendar.work_time_rate / 100.0

            for code in [
                    '205', '210', '211', '212', '213',
                    '305', '310', '311', '312', '313',
                    '340', '341', '342', '343']:
                report_data[code] = workers_data[code]

            # SECTION 580: Trainings
            training_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_training')
            training_code = training_type.code
            training_payslips = payslips.filtered(lambda p: training_code in p.worked_days_line_ids.mapped('work_entry_type_id.code'))
            male_payslips = training_payslips.filtered(lambda p: p.employee_id.gender == 'male')
            female_payslips = training_payslips - male_payslips

            report_data['5801'] = len(male_payslips.mapped('employee_id'))
            report_data['5811'] = len(female_payslips.mapped('employee_id'))

            report_data['5802'] = male_payslips._get_worked_days_line_number_of_hours(training_code)
            report_data['5812'] = female_payslips._get_worked_days_line_number_of_hours(training_code)

            report_data['58031'] = male_payslips._get_worked_days_line_amount(training_code)
            report_data['58131'] = female_payslips._get_worked_days_line_amount(training_code)

            line_values = (male_payslips + female_payslips)._get_line_values(['SALARY', 'ONSSTOTAL'])
            report_data['58032'] = sum(p._get_worked_days_line_amount(training_code) / line_values['SALARY'][p.id]['total'] * line_values['ONSSTOTAL'][p.id]['total'] for p in male_payslips)
            report_data['58132'] = sum(p._get_worked_days_line_amount(training_code) / line_values['SALARY'][p.id]['total'] * line_values['ONSSTOTAL'][p.id]['total'] for p in female_payslips)

            report_data['5803'] = report_data['58031'] + report_data['58032']
            report_data['5813'] = report_data['58131'] + report_data['58132']

            report_data['58033'] = 0
            report_data['58133'] = 0

            # For Informel trainings + inital training, we don't have any way to collect the data currently
            for code in ['5821', '5831', '5822', '5832', '5823', '5833', '5841', '5851', '5842', '5852', '5843', '5853']:
                report_data[code] = 0
            if i == number_of_months_period:
                reports_data['social_balance_sheet'] = report_data
                report_data['year'] = date_from.strftime('%Y')
            else:
                report_data['month'] = format_date(self.env, date_from, date_format='MMMM')
                report_data['year'] = date_from.strftime('%Y')
                reports_data['SBS{:0{}}'.format(i, max_int_len)] = report_data
        return collections.OrderedDict(sorted(reports_data.items(), key=lambda t: t[0], reverse=True))

    def print_report(self):
        report_data = self._get_report_data()
        filename = _(
            'SocialBalance-%(date_from)s-%(date_to)s.pdf',
            date_from=format_date(self.env, self.date_from),
            date_to=format_date(self.env, self.date_to))
        export_274_sheet_pdf, dummy = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            self.env.ref('l10n_be_hr_payroll.action_report_social_balance').id,
            res_ids=self.ids, data={'sbs_data': report_data})

        self.social_balance_filename = filename
        self.social_balance_sheet = base64.encodebytes(export_274_sheet_pdf)
        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Social Balance Sheet'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def export_report_xlsx(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sbs_worksheet = workbook.add_worksheet(_('Social Balance Sheet'))

        # styling
        style_header = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center', 'bottom': 1})
        style_special_header = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#875A7B', 'align': 'center', 'bottom': 1})
        style_vertical_header = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center', 'bottom': 1, 'right': 1})
        style_special_vertical_header = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#875A7B', 'align': 'center', 'bottom': 1, 'right': 1})
        style_normal = workbook.add_format({'align': 'center'})
        style_special_normal = workbook.add_format({'bg_color': '#B49DAE', 'align': 'center'})
        column_width = 20
        double_column_width = 2 * column_width
        triple_column_width = 3 * column_width

        # company worksheet
        company_header = _('Identification of the company')
        company_data = {
            'name': {
                'header': _('Name'),
                'value': self.company_id.name,
            },
            'vat': {
                'header': _('VAT Number'),
                'value': self.company_id.vat,
            },
            'onss': {
                'header': _('ONSS Number'),
                'value': self.company_id.onss_registration_number,
            },
            'established': {
                'header': _('Established on'),
                'value': _(
                    "%(established_date)s at %(established_time)s",
                    established_date=format_date(self.env, self.create_date, date_format='long'),
                    established_time=format_time(self.env, self.create_date),
                )
            },
            'joint_committees': {
                'header': _('Number of joint committees'),
                'value': 20000,
            },
            'period': {
                'header': _('Period'),
                'value': _(
                    '%(date_from)s to %(date_to)s',
                    date_from=format_date(self.env, self.date_from, date_format='long'),
                    date_to=format_date(self.env, self.date_to, date_format='long'),
                ),
            },
            'currency': {
                'header': _('Currency'),
                'value': self.company_id.currency_id.name,
            },
        }

        current_line = 0
        for i, data in enumerate(company_data.values()):
            sbs_worksheet.write(i + 1, 0, data['header'], style_vertical_header)
            sbs_worksheet.write(i + 1, 1, data['value'], style_normal)
            current_line += 1
        current_line += 2

        reports_data = self._get_report_data()
        for report_name, report_data in reports_data.items():
            if report_name != 'social_balance_sheet':
                current_worksheet = workbook.add_worksheet(_(
                    'SBS %(month)s %(year)s',
                    month=report_data['month'],
                    year=report_data['year']))
            else:
                current_worksheet = sbs_worksheet
            current_worksheet.set_column(0, 0, triple_column_width)
            current_worksheet.set_column(1, 1, double_column_width)
            current_worksheet.set_column(2, 4, column_width)
            current_worksheet.write(0, 0, company_header, style_header)
            current_worksheet.write(0, 1, '', style_vertical_header)
            headers_1000 = ['', 'Code', 'Total', 'Male', 'Female']
            for i, header in enumerate(headers_1000):
                current_worksheet.write(current_line, i, header, style_header)

            data_1000 = {
                '1001': {
                    'header': _('Average number of full-time workers'),
                    'values': [
                        1001,
                        report_data['1001_total'],
                        report_data['1001_male'],
                        report_data['1001_female'],
                    ],
                },
                '1002': {
                    'header': _('Average number of part-time workers'),
                    'values': [
                        1002,
                        report_data['1002_total'],
                        report_data['1002_male'],
                        report_data['1002_female'],
                    ],
                },
                '1003': {
                    'header': _('Average number of total workers or FTEs'),
                    'values': [
                        1003,
                        report_data['1003_total'],
                        report_data['1003_male'],
                        report_data['1003_female'],
                    ],
                },
                '1011': {
                    'header': _('Actual number of hours worked full time'),
                    'values': [
                        1011,
                        report_data['1011_total'],
                        report_data['1011_male'],
                        report_data['1011_female'],
                    ],
                },
                '1012': {
                    'header': _('Actual number of hours worked part-time'),
                    'values': [
                        1012,
                        report_data['1012_total'],
                        report_data['1012_male'],
                        report_data['1012_female'],
                    ],
                },
                '1013': {
                    'header': _('Total actual number of hours worked or FTE'),
                    'values': [
                        1013,
                        report_data['1013_total'],
                        report_data['1013_male'],
                        report_data['1013_female'],
                    ],
                },
            }

            for data in data_1000.values():
                current_line += 1
                current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                for i, value in enumerate(data['values']):
                    current_worksheet.write(current_line, i + 1, value, style_normal)

            headers_102 = ['102: Staff Costs:', 'Total', 'Male', 'Female']
            current_line += 2
            for i, header in enumerate(headers_102):
                current_worksheet.write(current_line, i, header, style_header)

            data_102 = {
                'full_time': {
                    'full_time': {
                        'header': _('Full Time'),
                        'values': ['', '', ''],
                    },
                    'total_gross': {
                        'header': _('Total Gross'),
                        'values': [
                            report_data['102']['total_gross']['male']['full']
                            + report_data['102']['total_gross']['female']['full'],
                            report_data['102']['total_gross']['male']['full'],
                            report_data['102']['total_gross']['female']['full'],
                        ],
                    },
                    'salaries_paid': {
                        'header': _('Salaries paid in relation to previous years'),
                        'values': ['', '', ''],
                    },
                    'reimbursed_expenses': {
                        'header': _('Reimbursed Expenses'),
                        'values': [
                            report_data['102']['reimbursed_expenses']['male']['full']
                            + report_data['102']['reimbursed_expenses']['female']['full'],
                            report_data['102']['reimbursed_expenses']['male']['full'],
                            report_data['102']['reimbursed_expenses']['female']['full'],
                        ],
                    },
                    'reimbursed_expenses_code_330': {
                        'header': _('Reimbursed Expenses (Code 330)'),
                        'values': ['', '', ''],
                    },
                    'foreign_expenses': {
                        'header': _('Foreign Expenses'),
                        'values': ['', '', ''],
                    },
                    'private_car': {
                        'header': _('Private Car'),
                        'values': [
                            report_data['102']['private_car']['male']['full']
                            + report_data['102']['private_car']['female']['full'],
                            report_data['102']['private_car']['male']['full'],
                            report_data['102']['private_car']['female']['full'],
                        ],
                    },
                    'public_transport': {
                        'header': _('Public Transportation'),
                        'values': [
                            report_data['102']['public_transport']['male']['full']
                            + report_data['102']['public_transport']['female']['full'],
                            report_data['102']['public_transport']['male']['full'],
                            report_data['102']['public_transport']['female']['full'],
                        ],
                    },
                    'mobility_bonus': {
                        'header': _('Mobility Bonus'),
                        'values': ['', '', ''],
                    },
                    'withdrawal_not_retained': {
                        'header': _('Withdrawal not retained'),
                        'values': ['', '', ''],
                    },
                    'onss_employer': {
                        'header': _('ONNS Employer'),
                        'values': [
                            report_data['102']['onss_employer']['male']['full']
                            + report_data['102']['onss_employer']['female']['full'],
                            report_data['102']['onss_employer']['male']['full'],
                            report_data['102']['onss_employer']['female']['full'],
                        ],
                    },
                    'overseas_social_security': {
                        'header': _('Overseas Social Security'),
                        'values': ['', '', ''],
                    },
                    'youth_hiring_plan': {
                        'header': _('Youth Hiring Plan'),
                        'values': ['', '', ''],
                    },
                    'employer_contribution_to_fund': {
                        'header': _('Employer contribution to the fund'),
                        'values': ['', '', ''],
                    },
                    'other_employer_contributions': {
                        'header': _('Other employer contributions'),
                        'values': ['', '', ''],
                    },
                    'total_full_time_code_1021': {
                        'header': _('Total Full Time (code 1021)'),
                        'values': [
                            report_data['102']['total']['male']['full']
                            + report_data['102']['total']['female']['full'],
                            report_data['102']['total']['male']['full'],
                            report_data['102']['total']['female']['full'],
                        ],
                    },
                },
                'part_time': {
                    'part_time': {
                        'header': _('Part Time'),
                        'values': ['', '', ''],
                    },
                    'total_gross': {
                        'header': _('Total Gross'),
                        'values': [
                            report_data['102']['total_gross']['male']['part']
                            + report_data['102']['total_gross']['female']['part'],
                            report_data['102']['total_gross']['male']['part'],
                            report_data['102']['total_gross']['female']['part'],
                        ],
                    },
                    'salaries_paid': {
                        'header': _('Salaries paid in relation to previous years'),
                        'values': ['', '', ''],
                    },
                    'reimbursed_expenses': {
                        'header': _('Reimbursed Expenses'),
                        'values': [
                            report_data['102']['reimbursed_expenses']['male']['part']
                            + report_data['102']['reimbursed_expenses']['female']['part'],
                            report_data['102']['reimbursed_expenses']['male']['part'],
                            report_data['102']['reimbursed_expenses']['female']['part'],
                        ],
                    },
                    'reimbursed_expenses_code_330': {
                        'header': _('Reimbursed Expenses (Code 330)'),
                        'values': ['', '', ''],
                    },
                    'foreign_expenses': {
                        'header': _('Foreign Expenses'),
                        'values': ['', '', ''],
                    },
                    'private_car': {
                        'header': _('Private Car'),
                        'values': [
                            report_data['102']['private_car']['male']['part']
                            + report_data['102']['private_car']['female']['part'],
                            report_data['102']['private_car']['male']['part'],
                            report_data['102']['private_car']['female']['part'],
                        ],
                    },
                    'public_transport': {
                        'header': _('Public Transportation'),
                        'values': [
                            report_data['102']['public_transport']['male']['part']
                            + report_data['102']['public_transport']['female']['part'],
                            report_data['102']['public_transport']['male']['part'],
                            report_data['102']['public_transport']['female']['part'],
                        ],
                    },
                    'mobility_bonus': {
                        'header': _('Mobility Bonus'),
                        'values': ['', '', ''],
                    },
                    'withdrawal_not_retained': {
                        'header': _('Withdrawal not retained'),
                        'values': ['', '', ''],
                    },
                    'onss_employer': {
                        'header': _('ONNS Employer'),
                        'values': [
                            report_data['102']['onss_employer']['male']['part']
                            + report_data['102']['onss_employer']['female']['part'],
                            report_data['102']['onss_employer']['male']['part'],
                            report_data['102']['onss_employer']['female']['part'],
                        ],
                    },
                    'overseas_social_security': {
                        'header': _('Overseas Social Security'),
                        'values': ['', '', ''],
                    },
                    'youth_hiring_plan': {
                        'header': _('Youth Hiring Plan'),
                        'values': ['', '', ''],
                    },
                    'employer_contribution_to_fund': {
                        'header': _('Employer contribution to the fund'),
                        'values': ['', '', ''],
                    },
                    'other_employer_contributions': {
                        'header': _('Other employer contributions'),
                        'values': ['', '', ''],
                    },
                    'total_part_time_code_1022': {
                        'header': _('Total Part Time (code 1022)'),
                        'values': [
                            report_data['102']['total']['male']['part']
                            + report_data['102']['total']['female']['part'],
                            report_data['102']['total']['male']['part'],
                            report_data['102']['total']['female']['part'],
                        ],
                    },
                },
                'total': {
                    'total_full_time_part_time_code_1023': {
                        'header': _('Total Full Time + Part Time (code 1023)'),
                        'values': [
                            report_data['102']['total']['male']['part']
                            + report_data['102']['total']['female']['part']
                            + report_data['102']['total']['male']['full']
                            + report_data['102']['total']['female']['full'],
                            report_data['102']['total']['male']['full']
                            + report_data['102']['total']['male']['part'],
                            report_data['102']['total']['female']['full']
                            + report_data['102']['total']['female']['part'],
                        ],
                    },
                },
            }

            for inner_dictionary in data_102.values():
                for i, data in enumerate(inner_dictionary.values()):
                    current_line += 1
                    if not i:
                        current_worksheet.write(current_line, 0, data['header'], style_special_vertical_header)
                        for j, value in enumerate(data['values']):
                            current_worksheet.write(current_line, j + 1, value, style_special_normal)
                        continue

                    current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                    for j, value in enumerate(data['values']):
                        current_worksheet.write(current_line, j + 1, value, style_normal)

            hearders_103 = ['103: Benefits Above Salary:', 'Total', 'Male', 'Female']
            current_line += 2
            for i, header in enumerate(hearders_103):
                current_worksheet.write(current_line, i, header, style_header)

            data_103 = {
                'full_time': {
                    'header': _('Full Time'),
                    'values': [
                        report_data['103']['male'] + report_data['103']['female'],
                        report_data['103']['male'],
                        report_data['103']['female'],
                    ],
                },
            }

            for data in data_103.values():
                current_line += 1
                current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                for i, value in enumerate(data['values']):
                    current_worksheet.write(current_line, i + 1, value, style_normal)

            headers_eoe = ['', 'Code', 'Full Time', 'Part Time', 'Total (FTE)']
            current_line += 2
            for i, header in enumerate(headers_eoe):
                current_worksheet.write(current_line, i, header, style_header)

            data_eoe = {
                '105': {
                    'number_of_workers': {
                        'header': _('Number of Workers'),
                        'values': [
                            105,
                            report_data['105']['full'],
                            report_data['105']['part'],
                            report_data['105']['fte'],
                        ],
                    },
                },
                '11x': {
                    'by_contract_type': {
                        'header': _('By Contract Type'),
                        'values': ['', '', '', ''],
                    },
                    'permanent_contract_cdi': {
                        'header': _('Permanent contract (CDI)'),
                        'values': [
                            110,
                            report_data['110']['full'],
                            report_data['110']['part'],
                            report_data['110']['fte'],
                        ],
                    },
                    'fixed_term_contract_cdd': {
                        'header': _('Fixed-term contract (CDD)'),
                        'values': [
                            111,
                            report_data['111']['full'],
                            report_data['111']['part'],
                            report_data['111']['fte'],
                        ],
                    },
                    'contract_execution_clearly_defined_work': {
                        'header': _('Contract for the execution of a clearly defined work'),
                        'values': [
                            112,
                            report_data['112']['full'],
                            report_data['112']['part'],
                            report_data['112']['fte'],
                        ],
                    },
                    'replacement_contract': {
                        'header': _('Replacement contract'),
                        'values': [
                            113,
                            report_data['113']['part'],
                            report_data['113']['full'],
                            report_data['113']['fte'],
                        ],
                    },
                },
                'by_gender': {
                    'by_gender': {
                        'header': _('By Gender'),
                        'values': ['', '', '', ''],
                    },
                },
                'male': {
                    'male': {
                        'header': _('Male'),
                        'values': [
                            120,
                            report_data['120']['full'],
                            report_data['120']['part'],
                            report_data['120']['fte'],
                        ],
                    },
                    'primary_education': {
                        'header': _('Primary education'),
                        'values': [
                            1200,
                            report_data['1200']['full'],
                            report_data['1200']['part'],
                            report_data['1200']['fte'],
                        ],
                    },
                    'secondary_education': {
                        'header': _('Secondary education'),
                        'values': [
                            1201,
                            report_data['1201']['full'],
                            report_data['1201']['part'],
                            report_data['1201']['fte'],
                        ],
                    },
                    'non_university_higher_education': {
                        'header': _('Non-university higher education'),
                        'values': [
                            1202,
                            report_data['1202']['full'],
                            report_data['1202']['part'],
                            report_data['1202']['fte'],
                        ],
                    },
                    'university_education': {
                        'header': _('University education'),
                        'values': [
                            1203,
                            report_data['1203']['full'],
                            report_data['1203']['part'],
                            report_data['1203']['fte'],
                        ],
                    },
                },
                'female': {
                    'female': {
                        'header': _('Female'),
                        'values': [
                            121,
                            report_data['121']['full'],
                            report_data['121']['part'],
                            report_data['121']['fte'],
                        ],
                    },
                    'primary_education': {
                        'header': _('Primary education'),
                        'values': [
                            1210,
                            report_data['1210']['full'],
                            report_data['1210']['part'],
                            report_data['1210']['fte'],
                        ],
                    },
                    'secondary_education': {
                        'header': _('Secondary education'),
                        'values': [
                            1211,
                            report_data['1211']['full'],
                            report_data['1211']['part'],
                            report_data['1211']['fte'],
                        ],
                    },
                    'non_university_higher_education': {
                        'header': _('Non-university higher education'),
                        'values': [
                            1212,
                            report_data['1212']['full'],
                            report_data['1212']['part'],
                            report_data['1212']['fte'],
                        ],
                    },
                    'university_education': {
                        'header': _('University education'),
                        'values': [
                            1213,
                            report_data['1213']['full'],
                            report_data['1213']['part'],
                            report_data['1213']['fte'],
                        ],
                    },
                },
                'by_professional_category': {
                    'by_professional_category': {
                        'header': _('By professional category'),
                        'values': ['', '', '', ''],
                    },
                    'management_staff': {
                        'header': _('Management staff'),
                        'values': [
                            130,
                            report_data['130']['full'],
                            report_data['130']['part'],
                            report_data['130']['fte'],
                        ],
                    },
                    'employees': {
                        'header': _('Employees'),
                        'values': [
                            134,
                            report_data['134']['full'],
                            report_data['134']['part'],
                            report_data['134']['fte'],
                        ],
                    },
                    'workers': {
                        'header': _('Workers'),
                        'values': [
                            132,
                            report_data['132']['full'],
                            report_data['132']['part'],
                            report_data['132']['fte'],
                        ],
                    },
                    'others': {
                        'header': _('Others'),
                        'values': [
                            133,
                            report_data['133']['full'],
                            report_data['133']['part'],
                            report_data['133']['fte'],
                        ],
                    },
                },
            }

            for inner_dictionary in data_eoe.values():
                for i, data in enumerate(inner_dictionary.values()):
                    current_line += 1
                    if data['header'].startswith(_('By')):
                        current_worksheet.write(current_line, 0, data['header'], style_special_vertical_header)
                        for j, value in enumerate(data['values']):
                            current_worksheet.write(current_line, j + 1, value, style_special_normal)
                        continue

                    current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                    for j, value in enumerate(data['values']):
                        current_worksheet.write(current_line, j + 1, value, style_normal)

            headers_200 = ['', 'Code', 'Full Time', 'Part Time', 'Total (FTE)']
            current_line += 2
            for i, header in enumerate(headers_200):
                current_worksheet.write(current_line, i, header, style_special_header)

            data_200 = {
                '205': {
                    'header': _('Total'),
                    'values': [
                        205,
                        report_data['205']['full'],
                        report_data['205']['part'],
                        report_data['205']['fte'],
                    ],
                },
                '210': {
                    'header': _('Permanent contract (CDI)'),
                    'values': [
                        210,
                        report_data['210']['full'],
                        report_data['210']['part'],
                        report_data['210']['fte'],
                    ],
                },
                '211': {
                    'header': _('Fixed-term contract (CDD)'),
                    'values': [
                        211,
                        report_data['211']['full'],
                        report_data['211']['part'],
                        report_data['211']['fte'],
                    ],
                },
                '212': {
                    'header': _('Contract for the execution of a clearly defined work'),
                    'values': [
                        212,
                        report_data['212']['full'],
                        report_data['212']['part'],
                        report_data['212']['fte'],
                    ],
                },
                '213': {
                    'header': _('Replacement contract'),
                    'values': [
                        213,
                        report_data['213']['full'],
                        report_data['213']['part'],
                        report_data['213']['fte'],
                    ],
                },
            }

            for data in data_200.values():
                current_line += 1
                current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                for i, value in enumerate(data['values']):
                    current_worksheet.write(current_line, i + 1, value, style_normal)

            headers_300 = ['Departures', 'Code', 'Full Time', 'Part Time', 'Total (FTE)']
            current_line += 2
            for i, header in enumerate(headers_300):
                current_worksheet.write(current_line, i, header, style_special_header)

            data_300 = {
                '305': {
                    'header': _('Total'),
                    'values': [
                        305,
                        report_data['305']['full'],
                        report_data['305']['part'],
                        report_data['305']['fte'],
                    ],
                },
                '310': {
                    'header': _('Permanent contract (CDI)'),
                    'values': [
                        310,
                        report_data['310']['full'],
                        report_data['310']['part'],
                        report_data['310']['fte'],
                    ],
                },
                '311': {
                    'header': _('Fixed-term contract (CDD)'),
                    'values': [
                        311,
                        report_data['311']['full'],
                        report_data['311']['part'],
                        report_data['311']['fte'],
                    ],
                },
                '312': {
                    'header': _('Contract for the execution of a clearly defined work'),
                    'values': [
                        312,
                        report_data['312']['full'],
                        report_data['312']['part'],
                        report_data['312']['fte'],
                    ],
                },
                '313': {
                    'header': _('Replacement contract'),
                    'values': [
                        313,
                        report_data['313']['full'],
                        report_data['313']['part'],
                        report_data['313']['fte'],
                    ],
                },
                'by_reason_for_termination_of_the_contract': {
                    'header': _('By reason for termination of the contract'),
                    'values': ['', '', '', ''],
                },
                '340': {
                    'header': _('Pension'),
                    'values': [
                        340,
                        report_data['340']['full'],
                        report_data['340']['part'],
                        report_data['340']['fte'],
                    ],
                },
                '341': {
                    'header': _('Unemployment with company supplement'),
                    'values': [
                        341,
                        report_data['341']['full'],
                        report_data['341']['part'],
                        report_data['341']['fte'],
                    ],
                },
                '342': {
                    'header': _('Dismissal'),
                    'values': [
                        342,
                        report_data['342']['full'],
                        report_data['342']['part'],
                        report_data['342']['fte'],
                    ],
                },
                '343': {
                    'header': _('Another reason'),
                    'values': [
                        343,
                        report_data['343']['full'],
                        report_data['343']['part'],
                        report_data['343']['fte'],
                    ],
                },
            }

            for data in data_300.values():
                current_line += 1
                current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                for i, value in enumerate(data['values']):
                    current_worksheet.write(current_line, i + 1, value, style_normal)

            headers_580 = ["Formal continuous trainings at the employer's expense", 'Code', 'Male', 'Code', 'Female']
            current_line += 2
            for i, header in enumerate(headers_580):
                current_worksheet.write(current_line, i, header, style_special_header)

            data_580 = {
                '58x1': {
                    'header': _('Number of Affected Employees'),
                    'values': [
                        5801,
                        report_data['5801'],
                        5811,
                        report_data['5811'],
                    ],
                },
                '58x2': {
                    'header': _('Number of completed training hours'),
                    'values': [
                        5802,
                        report_data['5802'],
                        5812,
                        report_data['5812'],
                    ],
                },
                '58x3': {
                    'header': _('Net cost to the business'),
                    'values': [
                        5803,
                        report_data['5803'],
                        5813,
                        report_data['5813'],
                    ],
                },
                '58x31': {
                    'header': _('Gross cost directly linked to training'),
                    'values': [
                        58031,
                        report_data['58031'],
                        58131,
                        report_data['58131'],
                    ],
                },
                '58x32': {
                    'header': _('Contributions paid and payments to collective funds'),
                    'values': [
                        58032,
                        report_data['58032'],
                        58132,
                        report_data['58132'],
                    ],
                },
                '58x33': {
                    'header': _('Grants and other financial benefits received (to be deducted)'),
                    'values': [
                        58033,
                        report_data['58033'],
                        58133,
                        report_data['58133'],
                    ],
                },
            }

            for data in data_580.values():
                current_line += 1
                current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                for i, value in enumerate(data['values']):
                    current_worksheet.write(current_line, i + 1, value, style_normal)

            headers_582 = ["Informal continuous trainings at the employer's expense", 'Code', 'Male', 'Code', 'Female']
            current_line += 2
            for i, header in enumerate(headers_582):
                current_worksheet.write(current_line, i, header, style_special_header)

            data_582 = {
                '58x1': {
                    'header': _('Number of Affected Employees'),
                    'values': [
                        5821,
                        report_data['5821'],
                        5831,
                        report_data['5831'],
                    ],
                },
                '58x2': {
                    'header': _('Number of completed training hours'),
                    'values': [
                        5822,
                        report_data['5822'],
                        5832,
                        report_data['5832'],
                    ],
                },
                '58x3': {
                    'header': _('Net cost to the business'),
                    'values': [
                        5823,
                        report_data['5823'],
                        5833,
                        report_data['5833'],
                    ],
                },
            }

            for data in data_582.values():
                current_line += 1
                current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                for i, value in enumerate(data['values']):
                    current_worksheet.write(current_line, i + 1, value, style_normal)

            headers_584 = ["Initial trainings at the employer's expense", 'Code', 'Male', 'Code', 'Female']
            current_line += 2
            for i, header in enumerate(headers_584):
                current_worksheet.write(current_line, i, header, style_special_header)

            data_584 = {
                '58x1': {
                    'header': _('Number of Affected Employees'),
                    'values': [
                        5841,
                        report_data['5841'],
                        5851,
                        report_data['5851'],
                    ],
                },
                '58x2': {
                    'header': _('Number of completed training hours'),
                    'values': [
                        5842,
                        report_data['5842'],
                        5852,
                        report_data['5852'],
                    ],
                },
                '58x3': {
                    'header': _('Net cost to the business'),
                    'values': [
                        5843,
                        report_data['5843'],
                        5853,
                        report_data['5853'],
                    ],
                },
            }

            for data in data_584.values():
                current_line += 1
                current_worksheet.write(current_line, 0, data['header'], style_vertical_header)
                for i, value in enumerate(data['values']):
                    current_worksheet.write(current_line, i + 1, value, style_normal)
            current_line = 0

        workbook.close()

        base64_xlsx = base64.encodebytes(output.getvalue())
        filename = _(
            'SocialBalance-%(date_from)s-%(date_to)s.xlsx',
            date_from=format_date(self.env, self.date_from),
            date_to=format_date(self.env, self.date_to))
        self.social_balance_filename_xlsx = filename
        self.social_balance_xlsx = base64_xlsx
        self.state_xlsx = 'done'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Social Balance Sheet'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_validate(self):
        self.ensure_one()
        if self.social_balance_sheet:
            self._post_process_generated_file(self.social_balance_sheet, self.social_balance_filename)
        return {'type': 'ir.actions.act_window_close'}

    # To be overwritten in documents_l10n_be_hr_payroll to create a document.document
    def _post_process_generated_file(self, data, filename):
        return
