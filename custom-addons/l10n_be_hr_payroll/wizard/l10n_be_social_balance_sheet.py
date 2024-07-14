# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import collections

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    social_balance_sheet = fields.Binary('Social Balance Sheet', readonly=True, attachment=False)
    social_balance_filename = fields.Char()

    def print_report(self):
        self.ensure_one()
        report_data = {}

        contracts = self.env['hr.employee']._get_all_contracts(self.date_from, self.date_to, states=['open', 'close'])
        invalid_employees = contracts.employee_id.filtered(lambda e: e.gender not in ['male', 'female'])
        if invalid_employees:
            raise UserError(_('Please configure a gender (either male or female) for the following employees:\n\n%s', '\n'.join(invalid_employees.mapped('name'))))

        date_from = self.date_from + relativedelta(day=1)
        date_to = self.date_to + relativedelta(day=31)

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
            gender = contract.employee_id.gender
            calendar = contract.resource_calendar_id
            contract_time = 'full' if calendar.full_time_required_hours == calendar.hours_per_week else 'part'

            workers_data['105'][contract_time] += 1
            workers_data['105']['fte'] += 1 * calendar.work_time_rate / 100.0

            if contract.contract_type_id not in mapped_types:
                raise UserError(_("The contract %s for %s is not of one the following types: CDI, CDD. Replacement, For a clearly defined work", contract.name, contract.employee_id.name))
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

            structure_type = contract.structure_type_id
            if cip and contract.contract_type_id == cip:
                # CIP Contracts are considered as trainees
                structure_type = cp200_students

            if structure_type not in mapped_categories:
                raise UserError(_("The contract %s for %s is not of one the following types: CP200 Employees or Student", contract.name, contract.employee_id.name))
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
            calendar = contract.resource_calendar_id
            contract_time = 'full' if calendar.full_time_required_hours == calendar.hours_per_week else 'part'
            if employee not in in_employees and employee.first_contract_date and (date_from <= employee.first_contract_date <= date_to):
                in_employees |= employee

                workers_data['205'][contract_time] += 1
                workers_data['205']['fte'] += 1 * calendar.work_time_rate / 100.0

                if contract.contract_type_id not in in_mapped_types:
                    raise UserError(_("The contract %s for %s is not of one the following types: CDI, CDD. Replacement, For a clearly defined work", contract.name, contract.employee_id.name))
                contract_type = in_mapped_types[contract.contract_type_id]
                workers_data[contract_type][contract_time] += 1
                workers_data[contract_type]['fte'] += 1 * calendar.work_time_rate / 100.0
            departure_date = employee.end_notice_period or employee.departure_date
            if departure_date and employee not in out_employees and (date_from <= departure_date <= date_to):
                out_employees |= employee

                workers_data['305'][contract_time] += 1
                workers_data['305']['fte'] += 1 * calendar.work_time_rate / 100.0

                if contract.contract_type_id not in out_mapped_types:
                    raise UserError(_("The contract %s for %s is not of one the following types: CDI, CDD. Replacement, For a clearly defined work", contract.name, contract.employee_id.name))
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

        filename = 'SocialBalance-%s-%s.pdf' % (self.date_from.strftime("%d%B%Y"), self.date_to.strftime("%d%B%Y"))
        export_274_sheet_pdf, dummy = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            self.env.ref('l10n_be_hr_payroll.action_report_social_balance').id,
            res_ids=self.ids, data=report_data)

        self.social_balance_filename = filename
        self.social_balance_sheet = base64.encodebytes(export_274_sheet_pdf)
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
        if self.social_balance_sheet:
            self._post_process_generated_file(self.social_balance_sheet, self.social_balance_filename)
        return {'type': 'ir.actions.act_window_close'}

    # To be overwritten in documents_l10n_be_hr_payroll to create a document.document
    def _post_process_generated_file(self, data, filename):
        return
