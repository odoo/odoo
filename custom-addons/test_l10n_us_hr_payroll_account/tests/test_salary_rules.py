# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


@tagged('post_install_l10n', 'post_install', '-at_install', 'us_payslips_validation')
class TestPayslipValidation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='generic_coa'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.us').id,
            'l10n_us_ca_ett_tax': True,
        })

        cls.env.user.tz = 'America/Los_Angeles'

        cls.work_contact = cls.env['res.partner'].create([{
            'name': "Test Employee",
            'company_id': cls.env.company.id,
        }])

        cls.work_address = cls.env['res.partner'].create([{
            'name': "US Office",
            'company_id': cls.env.company.id,
            'state_id': cls.env.ref('base.state_us_5').id,
        }])

        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 40 Hours/Week",
            'company_id': cls.env.company.id,
            'hours_per_day': 8.0,
            'tz': "America/Los_Angeles",
            'two_weeks_calendar': False,
            'hours_per_week': 40.0,
            'full_time_required_hours': 40.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 17.0, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 17.0, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 12.0, 13.0, "lunch"),
                ("2", 13.0, 17.0, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 17.0, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 17.0, "afternoon"),
            ]],
        }])

        cls.employee = cls.env['hr.employee'].create([{
            'name': "Test Employee",
            'work_contact_id': cls.work_contact.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.us').id,
            'address_id': cls.work_address.id,
            'l10n_us_state_filing_status': 'ca_status_1',
        }])

        cls.contract = cls.env['hr.contract'].create([{
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'structure_type_id': cls.env.ref('l10n_us_hr_payroll.structure_type_employee_us').id,
            'date_start': datetime.date(2018, 12, 31),
            'wage': 14000.0,
            'state': "open",
        }])

        cls.env.ref('l10n_us_hr_payroll.rule_parameter_ca_sui_rate_2023').parameter_value = "1.7"

    @classmethod
    def _generate_payslip(cls, date_from, date_to, struct_id=False):
        work_entries = cls.contract.generate_work_entries(date_from, date_to)
        payslip = cls.env['hr.payslip'].create([{
            'name': "Test Payslip",
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'company_id': cls.env.company.id,
            'struct_id': struct_id or cls.env.ref('l10n_us_hr_payroll.hr_payroll_structure_us_employee_salary').id,
            'date_from': date_from,
            'date_to': date_to,
        }])
        work_entries.action_validate()
        payslip.compute_sheet()
        return payslip

    def _validate_payslip(self, payslip, results):
        error = []
        line_values = payslip._get_line_values(set(results.keys()) | set(payslip.line_ids.mapped('code')))
        for code, value in results.items():
            payslip_line_value = line_values[code][payslip.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Code: %s - Expected: %s - Reality: %s" % (code, value, payslip_line_value))
        for line in payslip.line_ids:
            if line.code not in results:
                error.append("Missing Line: '%s' - %s," % (line.code, line_values[line.code][payslip.id]['total']))
        if error:
            error.append("Payslip Period: %s - %s" % (payslip.date_from, payslip.date_to))
            error.append("Payslip Actual Values: ")
            error.append("        {")
            for line in payslip.line_ids:
                error.append("            '%s': %s," % (line.code, line_values[line.code][payslip.id]['total']))
            error.append("        }")
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def _validate_move_lines(self, lines, results):
        error = []
        for code, move_type, amount in results:
            if not any(l.account_id.code == code and not float_compare(l[move_type], amount, 2) for l in lines):
                error.append("Couldn't find %s move line on account %s with amount %s" % (move_type, code, amount))
        if error:
            for line in lines:
                for move_type in ['credit', 'debit']:
                    if line[move_type]:
                        error.append('%s - %s - %s' % (line.account_id.code, move_type, line[move_type]))
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def test_001_semi_monthly(self):
        # A salaried employee with semi-monthly payment.
        # Benefits: No healthcare but pre-tax retirement contributions
        self.contract.write({
            'wage': 4791.69,
            'l10n_us_pre_retirement_amount': 27.0,
            'l10n_us_pre_retirement_type': 'percent',
            'schedule_pay': 'semi-monthly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 4791.69, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 10.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 80.0, places=2)

        payslip_results = {
            'BASIC': 4791.69,
            'GROSS': 4791.69,
            '401K': -1293.76,
            'TAXABLE': 3497.93,
            'FIT': -447.07,
            'SST': -297.08,
            'MEDICARE': -69.48,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -186.82,
            'CASDITAX': -43.13,
            'COMPANYSOCIAL': 297.08,
            'COMPANYMEDICARE': 69.48,
            'COMPANYFUTA': 287.5,
            'COMPANYSUI': 81.46,
            'COMPANYCAETT': 4.79,
            'NET': 2454.36,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_002_semi_monthly_commission(self):
        # A Salaried employee plus commissions with semi-monthly payment
        # Benefits: Healthcare contributions, post-tax retirement contributions
        self.contract.write({
            'wage': 2398.68,
            'l10n_us_health_benefits_medical': 42.87,
            'l10n_us_health_benefits_dental': 3.69,
            'l10n_us_health_benefits_vision': 0.49,
            'l10n_us_health_benefits_fsa': 22.73,
            'l10n_us_post_roth_401k_amount': 8,
            'schedule_pay': 'semi-monthly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip.write({
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_us_hr_payroll.input_commission').id,
                'amount': 3365.6,
            })]
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 1)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2398.68, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 10.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 80.0, places=2)

        payslip_results = {
            'BASIC': 2398.68,
            'COMMISSION': 3365.6,
            'GROSS': 5764.28,
            'DENTAL': -3.69,
            'MEDICAL': -42.87,
            'VISION': -0.49,
            'MEDICALFSA': -22.73,
            'TAXABLE': 5694.5,
            'FIT': -953.18,
            'MEDICARE': -82.57,
            'MEDICAREADD': 0,
            'SST': -353.06,
            'CAINCOMETAX': -411.53,
            'CASDITAX': -51.25,
            'ROTH401K': -461.14,
            'COMPANYFUTA': 341.67,
            'COMPANYMEDICARE': 82.57,
            'COMPANYSOCIAL': 353.06,
            'COMPANYSUI': 96.81,
            'COMPANYCAETT': 5.69,
            'NET': 3381.77,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_003_hourly_wage(self):
        # An Hourly employee  (with a wage of $25 USD per hour)
        # Benefits: Healthcare contributions, no pre-tax retirement

        self.env['hr.work.entry'].create([{
            'name': 'Overtime',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'work_entry_type_id': self.env.ref('hr_work_entry.overtime_work_entry_type').id,
            'date_start': datetime.datetime(2023, 1, 1, 9),
            'date_stop': datetime.datetime(2023, 1, 1, 9) + relativedelta(hours=10, minutes=43, seconds=48),
            'company_id': self.env.company.id,
            'state': 'draft',
        }, {
            'name': 'Double Time',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'work_entry_type_id': self.env.ref('l10n_us_hr_payroll.double_work_entry_type').id,
            'date_start': datetime.datetime(2023, 1, 7, 9),
            'date_stop': datetime.datetime(2023, 1, 7, 9) + relativedelta(hours=1, minutes=10, seconds=12),
            'company_id': self.env.company.id,
            'state': 'draft',
        }, {
            'name': 'Retro Overtime',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'work_entry_type_id': self.env.ref('l10n_us_hr_payroll.retro_overtime_work_entry_type').id,
            'date_start': datetime.datetime(2023, 1, 7, 11),
            'date_stop': datetime.datetime(2023, 1, 7, 11) + relativedelta(hours=2, minutes=59, seconds=24),
            'company_id': self.env.company.id,
            'state': 'draft',
        }, {
            'name': 'Retro Regular Pay',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'work_entry_type_id': self.env.ref('l10n_us_hr_payroll.retro_regular_work_entry_type').id,
            'date_start': datetime.datetime(2023, 1, 8, 8),
            'date_stop': datetime.datetime(2023, 1, 9, 0),
            'company_id': self.env.company.id,
            'state': 'draft',
        }, {
            'name': 'Retro Regular Pay',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'work_entry_type_id': self.env.ref('l10n_us_hr_payroll.retro_regular_work_entry_type').id,
            'date_start': datetime.datetime(2023, 1, 14, 8),
            'date_stop': datetime.datetime(2023, 1, 15, 0),
            'company_id': self.env.company.id,
            'state': 'draft',
        }])

        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.contract.resource_calendar_id.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2023, 1, 2, 16, 0, 0),
            'date_to': datetime.datetime(2023, 1, 3, 1, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_leave').id
        }])

        self.contract.write({
            'wage_type': 'hourly',
            'schedule_pay': 'monthly',
            'hourly_wage': 25,
            'l10n_us_health_benefits_medical': 98.65,
            'l10n_us_health_benefits_dental': 6.97,
            'l10n_us_health_benefits_vision': 0.97,
        })
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        self.assertEqual(len(payslip.worked_days_line_ids), 6)
        self.assertEqual(len(payslip.input_line_ids), 0)

        wds = payslip.worked_days_line_ids.sorted("number_of_hours")
        self.assertEqual(wds[0].work_entry_type_id.code, "USDOUBLE")
        self.assertAlmostEqual(wds[0].number_of_days, 0.15, places=2)
        self.assertAlmostEqual(wds[0].number_of_hours, 1.17, places=2)
        self.assertAlmostEqual(wds[0].amount, 58.5, places=2)

        self.assertEqual(wds[1].work_entry_type_id.code, "USRETROOVERTIME")
        self.assertAlmostEqual(wds[1].number_of_days, 0.37, places=2)
        self.assertAlmostEqual(wds[1].number_of_hours, 2.99, places=2)
        self.assertAlmostEqual(wds[1].amount, 112.13, places=2)

        self.assertEqual(wds[2].work_entry_type_id.code, "LEAVE100")
        self.assertAlmostEqual(wds[2].number_of_days, 1, places=2)
        self.assertAlmostEqual(wds[2].number_of_hours, 8, places=2)
        self.assertAlmostEqual(wds[2].amount, 200.0, places=2)

        self.assertEqual(wds[3].work_entry_type_id.code, "OVERTIME")
        self.assertAlmostEqual(wds[3].number_of_days, 1.34, places=2)
        self.assertAlmostEqual(wds[3].number_of_hours, 10.73, places=2)
        self.assertAlmostEqual(wds[3].amount, 402.38, places=2)

        self.assertEqual(wds[4].work_entry_type_id.code, "USRETROREGULAR")
        self.assertAlmostEqual(wds[4].number_of_days, 4, places=2)
        self.assertAlmostEqual(wds[4].number_of_hours, 32, places=2)
        self.assertAlmostEqual(wds[4].amount, 800, places=2)

        self.assertEqual(wds[5].work_entry_type_id.code, "WORK100")
        self.assertAlmostEqual(wds[5].number_of_days, 9.0, places=2)
        self.assertAlmostEqual(wds[5].number_of_hours, 72, places=2)
        self.assertAlmostEqual(wds[5].amount, 1800, places=2)

        payslip_results = {
            'BASIC': 3373.01,
            'GROSS': 3373.01,
            'MEDICAL': -98.65,
            'DENTAL': -6.97,
            'VISION': -0.97,
            'TAXABLE': 3266.42,
            'FIT': -235.14,
            'SST': -202.52,
            'MEDICARE': -47.36,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -71.45,
            'CASDITAX': -29.4,
            'COMPANYSOCIAL': 202.52,
            'COMPANYMEDICARE': 47.36,
            'COMPANYFUTA': 195.99,
            'COMPANYSUI': 55.53,
            'COMPANYCAETT': 3.27,
            'NET': 2680.55,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_004_tax_status_married_jointly_old_w4(self):
        self.contract.write({
            'wage': 4791.69,
            'l10n_us_pre_retirement_amount': 27.0,
            'l10n_us_pre_retirement_type': 'percent',
            'schedule_pay': 'monthly',
        })

        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_step_2': True,
            'l10n_us_w4_allowances_count': 1,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_2',
        })
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 4791.69,
            'GROSS': 4791.69,
            '401K': -1293.76,
            'TAXABLE': 3497.93,
            'FIT': -192.09,
            'SST': -297.08,
            'MEDICARE': -69.48,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -36.05,
            'CASDITAX': -43.13,
            'COMPANYSOCIAL': 297.08,
            'COMPANYMEDICARE': 69.48,
            'COMPANYFUTA': 287.5,
            'COMPANYSUI': 81.46,
            'COMPANYCAETT': 4.79,
            'NET': 2860.11,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_005_tax_status_married_jointly_new_w4(self):
        self.contract.write({
            'wage': 4791.69,
            'schedule_pay': 'monthly',
        })

        self.employee.write({
            'l10n_us_w4_step_2': True,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_2',
        })
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 4791.69,
            'GROSS': 4791.69,
            'TAXABLE': 4791.69,
            'FIT': -418.17,
            'SST': -297.08,
            'MEDICARE': -69.48,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -85.39,
            'CASDITAX': -43.13,
            'COMPANYSOCIAL': 297.08,
            'COMPANYMEDICARE': 69.48,
            'COMPANYFUTA': 287.5,
            'COMPANYSUI': 81.46,
            'COMPANYCAETT': 4.79,
            'NET': 3878.44,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_006_ca_state_single_no_allowance(self):
        self.contract.write({
            'wage': 3416.68,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 256.86,
            'l10n_us_pre_retirement_type': 'fixed',
            'l10n_us_health_benefits_medical': 62.01,
            'l10n_us_health_benefits_dental': 2.48,
            'l10n_us_health_benefits_vision': 0.49,
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 15))
        payslip.write({
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_us_hr_payroll.input_commission').id,
                'amount': 864.29,
            })]
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 3416.68,
            'COMMISSION': 864.29,
            'GROSS': 4280.97,
            '401K': -256.86,
            'DENTAL': -2.48,
            'MEDICAL': -62.01,
            'VISION': -0.49,
            'TAXABLE': 3959.13,
            'FIT': -548.53,
            'MEDICARE': -61.13,
            'MEDICAREADD': 0,
            'SST': -261.39,
            'CAINCOMETAX': -234.0,
            'CASDITAX': -37.94,
            'COMPANYFUTA': 252.96,
            'COMPANYMEDICARE': 61.13,
            'COMPANYSOCIAL': 261.39,
            'COMPANYSUI': 71.67,
            'COMPANYCAETT': 4.22,
            'NET': 2816.14,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_007_ca_state_post_retirement(self):
        self.contract.write({
            'wage': 2398.68,
            'schedule_pay': 'semi-monthly',
            'l10n_us_health_benefits_medical': 42.87,
            'l10n_us_health_benefits_dental': 3.69,
            'l10n_us_health_benefits_vision': 0.49,
            'l10n_us_health_benefits_fsa': 22.73,
            'l10n_us_post_roth_401k_amount': 461.14,
            'l10n_us_post_roth_401k_type': 'fixed',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 15))
        payslip.write({
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_us_hr_payroll.input_commission').id,
                'amount': 3365.60,
            })]
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 2398.68,
            'COMMISSION': 3365.6,
            'GROSS': 5764.28,
            'DENTAL': -3.69,
            'MEDICAL': -42.87,
            'VISION': -0.49,
            'MEDICALFSA': -22.73,
            'TAXABLE': 5694.5,
            'FIT': -953.18,
            'MEDICARE': -82.57,
            'MEDICAREADD': 0,
            'SST': -353.06,
            'CAINCOMETAX': -411.53,
            'CASDITAX': -51.25,
            'ROTH401K': -461.14,
            'COMPANYFUTA': 341.67,
            'COMPANYMEDICARE': 82.57,
            'COMPANYSOCIAL': 353.06,
            'COMPANYSUI': 96.81,
            'COMPANYCAETT': 5.69,
            'NET': 3381.77,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_008_benefits_matching(self):
        self.contract.write({
            'wage': 4791.69,
            'l10n_us_pre_retirement_amount': 27.0,
            'l10n_us_pre_retirement_type': 'percent',
            'l10n_us_pre_retirement_matching_amount': 50.0,
            'l10n_us_pre_retirement_matching_type': 'percent',
            'schedule_pay': 'semi-monthly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 4791.69, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 10.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 80.0, places=2)

        payslip_results = {
            'BASIC': 4791.69,
            'GROSS': 4791.69,
            '401K': -1293.76,
            '401KMATCHING': 646.88,
            'TAXABLE': 3497.93,
            'FIT': -447.07,
            'SST': -297.08,
            'MEDICARE': -69.48,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -186.82,
            'CASDITAX': -43.13,
            'COMPANYSOCIAL': 297.08,
            'COMPANYMEDICARE': 69.48,
            'COMPANYFUTA': 287.5,
            'COMPANYSUI': 81.46,
            'COMPANYCAETT': 4.79,
            'NET': 2454.36,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_009_semi_monthly_cap_1_month(self):
        self.contract.write({
            'schedule_pay': 'semi-monthly',
            'wage': '30000',
            'l10n_us_pre_retirement_amount': 4500.0,
            'l10n_us_pre_retirement_type': 'fixed',
            'l10n_us_pre_retirement_matching_amount': 450,
            'l10n_us_pre_retirement_matching_type': 'fixed',
            'l10n_us_health_benefits_medical': 10.0,
            'l10n_us_health_benefits_dental': 10.0,
            'l10n_us_health_benefits_vision': 10.0,
            'l10n_us_health_benefits_fsa': 10.0,
            'l10n_us_health_benefits_fsadc': 10.0,
            'l10n_us_health_benefits_hsa': 10.0,
            'l10n_us_commuter_benefits': 10.0,
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 30000.0,
            'GROSS': 30000.0,
            '401K': -4500.0,
            '401KMATCHING': 450.0,
            'MEDICAL': -10.0,
            'DENTAL': -10.0,
            'VISION': -10.0,
            'MEDICALFSA': -10.0,
            'MEDICALFSADC': -10.0,
            'MEDICALHSA': -10.0,
            'COMMUTER': -10.0,
            'TAXABLE': 25430.0,
            'FIT': -7542.75,
            'SST': -1855.66,
            'MEDICARE': -433.99,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -2644.93,
            'CASDITAX': -269.46,
            'COMPANYSOCIAL': 1855.66,
            'COMPANYMEDICARE': 433.99,
            'COMPANYFUTA': 420.0,
            'COMPANYSUI': 119.0,
            'COMPANYCAETT': 7.0,
            'NET': 12683.22,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()

        payslip = self._generate_payslip(datetime.date(2023, 1, 16), datetime.date(2023, 1, 31))
        payslip_results = {
            'BASIC': 30000.0,
            'GROSS': 30000.0,
            '401K': -4500.0,
            '401KMATCHING': 450.0,
            'MEDICAL': -10.0,
            'DENTAL': -10.0,
            'VISION': -10.0,
            'MEDICALFSA': -10.0,
            'MEDICALFSADC': -10.0,
            'MEDICALHSA': -10.0,
            'COMMUTER': -10.0,
            'TAXABLE': 25430.0,
            'FIT': -7542.75,
            'SST': -1855.66,
            'MEDICARE': -433.99,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -2644.93,
            'CASDITAX': -269.46,
            'COMPANYSOCIAL': 1855.66,
            'COMPANYMEDICARE': 433.99,
            'COMPANYFUTA': 0,
            'COMPANYSUI': 0,
            'COMPANYCAETT': 0,
            'NET': 12683.22,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_010_semi_monthly_cap_6_months(self):
        self.env.ref('l10n_us_hr_payroll.rule_parameter_ca_sui_rate_2023').parameter_value = "6"

        self.contract.write({
            'schedule_pay': 'semi-monthly',
            'wage': '30000',
            'l10n_us_pre_retirement_amount': 4500.0,
            'l10n_us_pre_retirement_type': 'fixed',
            'l10n_us_pre_retirement_matching_amount': 450,
            'l10n_us_pre_retirement_matching_type': 'fixed',
            'l10n_us_health_benefits_medical': 10.0,
            'l10n_us_health_benefits_dental': 10.0,
            'l10n_us_health_benefits_vision': 10.0,
            'l10n_us_health_benefits_fsa': 10.0,
            'l10n_us_health_benefits_fsadc': 10.0,
            'l10n_us_health_benefits_hsa': 10.0,
            'l10n_us_commuter_benefits': 10.0,
            'l10n_us_post_roth_401k_amount': 4500.0,
            'l10n_us_post_roth_401k_type': 'fixed',
        })

        self.contract.generate_work_entries(datetime.date(2023, 1, 1), datetime.date(2023, 6, 30))

        all_payslips = self.env['hr.payslip']
        for month in range(1, 7):
            # First Payslip
            date_from = datetime.date(2023, month, 1)
            date_to = datetime.date(2023, month, 15)
            payslip = self._generate_payslip(date_from, date_to)
            all_payslips += payslip
            payslip.action_payslip_done()
            # Second Payslip
            date_from = datetime.date(2023, month, 16)
            date_to = datetime.date(2023, month, 1) + relativedelta(day=31)
            payslip = self._generate_payslip(date_from, date_to)
            all_payslips += payslip
            payslip.action_payslip_done()

        line_sums = {
            '401K': -22500,
            'COMPANYCAETT': 7,
            'COMPANYSUI': 420,
            'COMPANYFUTA': 420,
            'COMPANYSOCIAL': 9932.4,
            'ROTH401K': -22500,
        }
        line_values = all_payslips._get_line_values(line_sums.keys(), compute_sum=True)
        for code, total in line_sums.items():
            self.assertAlmostEqual(line_values[code]['sum']['total'], total)

    def test_011_additional_medicare(self):
        self.contract.write({
            'schedule_pay': 'semi-annually',
            'wage': 150000,
            'l10n_us_pre_retirement_amount': 4500.0,
            'l10n_us_pre_retirement_type': 'fixed',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 6, 30))
        payslip_results = {
            'BASIC': 150000.0,
            'GROSS': 150000.0,
            '401K': -4500.0,
            'TAXABLE': 145500.0,
            'FIT': -34448.5,
            'SST': -9300.0,
            'MEDICARE': -2175.0,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -12832.93,
            'CASDITAX': -1350.0,
            'COMPANYSOCIAL': 9300.0,
            'COMPANYMEDICARE': 2175.0,
            'COMPANYFUTA': 420.0,
            'COMPANYSUI': 119.0,
            'COMPANYCAETT': 7.0,
            'NET': 85393.57,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()
        additional_line = payslip.line_ids.filtered(lambda l: l.code == "MEDICAREADD")
        self.assertEqual(additional_line.rate, -0.9)
        self.assertEqual(additional_line.amount, 0)

        payslip = self._generate_payslip(datetime.date(2023, 7, 1), datetime.date(2023, 12, 31))
        payslip_results = {
            'BASIC': 150000.0,
            'GROSS': 150000.0,
            '401K': -4500.0,
            'TAXABLE': 145500.0,
            'FIT': -34448.5,
            'SST': -632.4,
            'MEDICARE': -2175.0,
            'MEDICAREADD': -900.0,
            'CAINCOMETAX': -12832.93,
            'CASDITAX': -1350.0,
            'COMPANYSOCIAL': 632.4,
            'COMPANYMEDICARE': 2175.0,
            'COMPANYFUTA': 0,
            'COMPANYSUI': 0,
            'COMPANYCAETT': 0,
            'NET': 93161.17,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()
        additional_line = payslip.line_ids.filtered(lambda l: l.code == "MEDICAREADD")
        self.assertEqual(additional_line.rate, -0.9)
        self.assertEqual(additional_line.amount, 100000.0)

    def test_012_benefits_matching_partial_cap(self):
        self.contract.write({
            'schedule_pay': 'semi-monthly',
            'wage': '30000',
            'l10n_us_pre_retirement_amount': 4500.0,
            'l10n_us_pre_retirement_type': 'fixed',
            'l10n_us_pre_retirement_matching_amount': 50,
            'l10n_us_pre_retirement_matching_type': 'percent',
            'l10n_us_pre_retirement_matching_yearly_cap': 6,
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 30000.0,
            'GROSS': 30000.0,
            '401K': -4500.0,
            '401KMATCHING': 900.0,
            'TAXABLE': 25500.0,
            'FIT': -7568.65,
            'SST': -1860.0,
            'MEDICARE': -435.0,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -2652.39,
            'CASDITAX': -270.0,
            'COMPANYSOCIAL': 1860.0,
            'COMPANYMEDICARE': 435.0,
            'COMPANYFUTA': 420.0,
            'COMPANYSUI': 119.0,
            'COMPANYCAETT': 7.0,
            'NET': 12713.96,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_013_state_tax_old_w4_use_case_1(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 0,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_1',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -463.29,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -289.33,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3319.88,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_013_state_tax_old_w4_use_case_2(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 1,
            'l10n_us_w4_withholding_deduction_allowances': 1,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_1',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -426.17,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -278.61,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3367.72,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_014_state_tax_old_w4_use_case_3(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 2,
            'l10n_us_w4_withholding_deduction_allowances': 2,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_1',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -404.67,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -268.01,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3399.83,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_015_state_tax_old_w4_use_case_4(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 0,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'separately',
            'l10n_us_state_filing_status': 'ca_status_2',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -752.5,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -160.21,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3159.79,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_016_state_tax_old_w4_use_case_5(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 1,
            'l10n_us_w4_withholding_deduction_allowances': 1,
            'l10n_us_filing_status': 'separately',
            'l10n_us_state_filing_status': 'ca_status_2',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -709.5,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -151.02,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3211.98,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_017_state_tax_old_w4_use_case_6(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 2,
            'l10n_us_w4_withholding_deduction_allowances': 2,
            'l10n_us_filing_status': 'separately',
            'l10n_us_state_filing_status': 'ca_status_2',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -667.52,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -127.58,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3277.4,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_018_state_tax_old_w4_use_case_7(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 0,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'single',
            'l10n_us_state_filing_status': 'ca_status_1',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -752.5,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -289.33,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3030.67,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_018_state_tax_old_w4_use_case_8(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 1,
            'l10n_us_w4_withholding_deduction_allowances': 1,
            'l10n_us_filing_status': 'single',
            'l10n_us_state_filing_status': 'ca_status_1',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -709.5,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -278.61,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3084.39,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_018_state_tax_old_w4_use_case_9(self):
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10,
            'l10n_us_pre_retirement_type': 'percent',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 2,
            'l10n_us_w4_withholding_deduction_allowances': 2,
            'l10n_us_filing_status': 'single',
            'l10n_us_state_filing_status': 'ca_status_1',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            '401K': -500.0,
            'TAXABLE': 4500.0,
            'FIT': -667.52,
            'SST': -310.0,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -268.01,
            'CASDITAX': -45.0,
            'COMPANYSOCIAL': 310.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYFUTA': 300.0,
            'COMPANYSUI': 85.0,
            'COMPANYCAETT': 5.0,
            'NET': 3136.97,
        }
        self._validate_payslip(payslip, payslip_results)

    # https://edd.ca.gov/siteassets/files/pdf_pub_ctr/23methb.pdf
    def test_050_state_tax_example_a(self):
        self.contract.write({
            'wage': 210,
            'schedule_pay': 'weekly',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 1,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'single',
            'l10n_us_state_filing_status': 'ca_status_1',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 210.0,
            'GROSS': 210.0,
            'TAXABLE': 210.0,
            'FIT': -2.63,
            'SST': -13.02,
            'MEDICARE': -3.05,
            'MEDICAREADD': 0,
            'CAINCOMETAX': 0,
            'CASDITAX': -1.89,
            'COMPANYSOCIAL': 13.02,
            'COMPANYMEDICARE': 3.05,
            'COMPANYFUTA': 12.6,
            'COMPANYSUI': 3.57,
            'COMPANYCAETT': 0.21,
            'NET': 189.41,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_051_state_tax_example_b(self):
        self.contract.write({
            'wage': 1600,
            'schedule_pay': 'bi-weekly',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 2,
            'l10n_us_w4_withholding_deduction_allowances': 1,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_2',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 1600.0,
            'GROSS': 1600.0,
            'TAXABLE': 1600.0,
            'FIT': -70.0,
            'SST': -99.2,
            'MEDICARE': -23.2,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -5.18,
            'CASDITAX': -14.4,
            'COMPANYSOCIAL': 99.2,
            'COMPANYMEDICARE': 23.2,
            'COMPANYFUTA': 96.0,
            'COMPANYSUI': 27.2,
            'COMPANYCAETT': 1.6,
            'NET': 1388.02,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_052_state_tax_example_c(self):
        self.contract.write({
            'wage': 5100,
            'schedule_pay': 'monthly',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 5,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_2',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 5100.0,
            'GROSS': 5100.0,
            'TAXABLE': 5100.0,
            'FIT': -212.33,
            'SST': -316.2,
            'MEDICARE': -73.95,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -15.73,
            'CASDITAX': -45.9,
            'COMPANYSOCIAL': 316.2,
            'COMPANYMEDICARE': 73.95,
            'COMPANYFUTA': 306.0,
            'COMPANYSUI': 86.7,
            'COMPANYCAETT': 5.1,
            'NET': 4435.88,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_053_state_tax_example_d(self):
        self.contract.write({
            'wage': 800,
            'schedule_pay': 'weekly',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 3,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'head',
            'l10n_us_state_filing_status': 'ca_status_4',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 800.0,
            'GROSS': 800.0,
            'TAXABLE': 800.0,
            'FIT': -49.88,
            'SST': -49.6,
            'MEDICARE': -11.6,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -0.04,
            'CASDITAX': -7.2,
            'COMPANYSOCIAL': 49.6,
            'COMPANYMEDICARE': 11.6,
            'COMPANYFUTA': 48.0,
            'COMPANYSUI': 13.6,
            'COMPANYCAETT': 0.8,
            'NET': 681.67,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_054_state_tax_example_e(self):
        self.contract.write({
            'wage': 2100,
            'schedule_pay': 'semi-monthly',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 4,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_2',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 2100.0,
            'GROSS': 2100.0,
            'TAXABLE': 2100.0,
            'FIT': -76.67,
            'SST': -130.2,
            'MEDICARE': -30.45,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -1.72,
            'CASDITAX': -18.9,
            'COMPANYSOCIAL': 130.2,
            'COMPANYMEDICARE': 30.45,
            'COMPANYFUTA': 126.0,
            'COMPANYSUI': 35.7,
            'COMPANYCAETT': 2.1,
            'NET': 1842.07,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_055_state_tax_example_f(self):
        self.contract.write({
            'wage': 57000,
            'schedule_pay': 'annually',
        })
        self.employee.write({
            'l10n_us_old_w4': True,
            'l10n_us_w4_allowances_count': 4,
            'l10n_us_w4_withholding_deduction_allowances': 0,
            'l10n_us_filing_status': 'jointly',
            'l10n_us_state_filing_status': 'ca_status_2',
        })

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 15))
        payslip_results = {
            'BASIC': 57000.0,
            'GROSS': 57000.0,
            'TAXABLE': 57000.0,
            'FIT': -2560.0,
            'SST': -3534.0,
            'MEDICARE': -826.5,
            'MEDICAREADD': 0,
            'CAINCOMETAX': -186.94,
            'CASDITAX': -513.0,
            'COMPANYSOCIAL': 3534.0,
            'COMPANYMEDICARE': 826.5,
            'COMPANYFUTA': 420.0,
            'COMPANYSUI': 119.0,
            'COMPANYCAETT': 7.0,
            'NET': 49379.56,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_056_tips(self):
        self.contract.write({
            'wage': 3416.68,
            'schedule_pay': 'semi-monthly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 15))
        payslip.write({
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_us_hr_payroll.input_tips').id,
                'amount': 500,
            }), (0, 0, {
                'input_type_id': self.env.ref('l10n_us_hr_payroll.input_allocated_tips').id,
                'amount': 300,
            })]
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 3416.68,
            'TIPS': 500.0,
            'GROSS': 3916.68,
            'TAXABLE': 3916.68,
            'FIT': -539.19,
            'MEDICARE': -56.79,
            'MEDICAREADD': 0,
            'SST': -242.83,
            'CAINCOMETAX': -229.65,
            'CASDITAX': -35.25,
            'COMPANYFUTA': 235.0,
            'COMPANYMEDICARE': 56.79,
            'COMPANYSOCIAL': 242.83,
            'COMPANYSUI': 66.58,
            'COMPANYCAETT': 3.92,
            'ALLOCATEDTIPS': 300.0,
            'NET': 3112.96,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_057_ny_state_tax_single_example_1(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 400,
            'schedule_pay': 'weekly',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 3,
            'l10n_us_state_filing_status': 'ny_status_1',
            'l10n_us_filing_status': 'single',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 7))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 400.0,
            'GROSS': 400.0,
            'TAXABLE': 400.0,
            'FIT': -13.37,
            'MEDICARE': -5.8,
            'MEDICAREADD': 0,
            'SST': -24.8,
            'NYINCOMETAX': -8.2,
            'NYSDITAX': -0.6,
            'NYPFLTAX': -1.82,
            'COMPANYFUTA': 24.0,
            'COMPANYMEDICARE': 5.8,
            'COMPANYSOCIAL': 24.8,
            'COMPANYSUI': 12.52,
            'COMPANYNYREEMPLOYMENT': 0.3,
            'NET': 345.41,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_058_ny_state_tax_single_example_2(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 1,
            'l10n_us_state_filing_status': 'ny_status_1',
            'l10n_us_filing_status': 'single',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 15))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            'TAXABLE': 5000.0,
            'FIT': -786.5,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'SST': -310.0,
            'NYINCOMETAX': -263.19,
            'NYSDITAX': -1.3,
            'NYPFLTAX': -22.75,
            'COMPANYFUTA': 300.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYSOCIAL': 310.0,
            'COMPANYSUI': 156.5,
            'COMPANYNYREEMPLOYMENT': 3.75,
            'NET': 3543.76,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_059_ny_state_tax_single_example_3(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 50000,
            'schedule_pay': 'monthly',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 3,
            'l10n_us_state_filing_status': 'ny_status_1',
            'l10n_us_filing_status': 'single',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 30))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 50000.0,
            'GROSS': 50000.0,
            'TAXABLE': 50000.0,
            'FIT': -14767.29,
            'MEDICARE': -725.0,
            'MEDICAREADD': 0,
            'SST': -3100.0,
            'NYINCOMETAX': -3576.71,
            'NYSDITAX': -2.6,
            'NYPFLTAX': -227.5,
            'COMPANYFUTA': 420.0,
            'COMPANYMEDICARE': 725.0,
            'COMPANYSOCIAL': 3100.0,
            'COMPANYSUI': 384.99,
            'COMPANYNYREEMPLOYMENT': 9.23,
            'NET': 27600.9,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_060_ny_state_tax_single_example_4(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 750,
            'schedule_pay': 'daily',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 2,
            'l10n_us_state_filing_status': 'ny_status_1',
            'l10n_us_filing_status': 'single',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 1))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 750.0,
            'GROSS': 750.0,
            'TAXABLE': 750.0,
            'FIT': -141.83,
            'MEDICARE': -10.88,
            'MEDICAREADD': 0,
            'SST': -46.5,
            'NYINCOMETAX': -44.83,
            'NYSDITAX': -0.09,
            'NYPFLTAX': -3.41,
            'COMPANYFUTA': 45.0,
            'COMPANYMEDICARE': 10.88,
            'COMPANYSOCIAL': 46.5,
            'COMPANYSUI': 23.48,
            'COMPANYNYREEMPLOYMENT': 0.56,
            'NET': 502.47,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_061_ny_state_tax_married_example_1(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 400,
            'schedule_pay': 'weekly',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 4,
            'l10n_us_state_filing_status': 'ny_status_2',
            'l10n_us_filing_status': 'jointly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 7))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 400.0,
            'GROSS': 400.0,
            'TAXABLE': 400.0,
            'FIT': 0,
            'MEDICARE': -5.8,
            'MEDICAREADD': 0,
            'SST': -24.8,
            'NYINCOMETAX': -6.86,
            'NYSDITAX': -0.6,
            'NYPFLTAX': -1.82,
            'COMPANYFUTA': 24.0,
            'COMPANYMEDICARE': 5.8,
            'COMPANYSOCIAL': 24.8,
            'COMPANYSUI': 12.52,
            'COMPANYNYREEMPLOYMENT': 0.3,
            'NET': 360.12,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_062_ny_state_tax_single_example_2(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 5000,
            'schedule_pay': 'semi-monthly',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 3,
            'l10n_us_state_filing_status': 'ny_status_2',
            'l10n_us_filing_status': 'jointly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 15))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            'TAXABLE': 5000.0,
            'FIT': -455.04,
            'MEDICARE': -72.5,
            'MEDICAREADD': 0,
            'SST': -310.0,
            'NYINCOMETAX': -252.68,
            'NYSDITAX': -1.3,
            'NYPFLTAX': -22.75,
            'COMPANYFUTA': 300.0,
            'COMPANYMEDICARE': 72.5,
            'COMPANYSOCIAL': 310.0,
            'COMPANYSUI': 156.5,
            'COMPANYNYREEMPLOYMENT': 3.75,
            'NET': 3885.73,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_063_ny_state_tax_single_example_3(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 50000,
            'schedule_pay': 'monthly',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 3,
            'l10n_us_state_filing_status': 'ny_status_2',
            'l10n_us_filing_status': 'jointly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 30))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 50000.0,
            'GROSS': 50000.0,
            'TAXABLE': 50000.0,
            'FIT': -12007.83,
            'MEDICARE': -725.0,
            'MEDICAREADD': 0,
            'SST': -3100.0,
            'NYINCOMETAX': -3622.01,
            'NYSDITAX': -2.6,
            'NYPFLTAX': -227.5,
            'COMPANYFUTA': 420.0,
            'COMPANYMEDICARE': 725.0,
            'COMPANYSOCIAL': 3100.0,
            'COMPANYSUI': 384.99,
            'COMPANYNYREEMPLOYMENT': 9.23,
            'NET': 30315.06,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_064_ny_state_tax_single_example_4(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 750,
            'schedule_pay': 'daily',
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 2,
            'l10n_us_state_filing_status': 'ny_status_2',
            'l10n_us_filing_status': 'jointly',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 1))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 750.0,
            'GROSS': 750.0,
            'TAXABLE': 750.0,
            'FIT': -105.47,
            'MEDICARE': -10.88,
            'MEDICAREADD': 0,
            'SST': -46.5,
            'NYINCOMETAX': -45.29,
            'NYSDITAX': -0.09,
            'NYPFLTAX': -3.41,
            'COMPANYFUTA': 45.0,
            'COMPANYMEDICARE': 10.88,
            'COMPANYSOCIAL': 46.5,
            'COMPANYSUI': 23.48,
            'COMPANYNYREEMPLOYMENT': 0.56,
            'NET': 538.37,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_065_ny_state_tax_common(self):
        # Source https://www.tax.ny.gov/pdf/publications/withholding/nys50_t_nys_123.pdf
        self.work_address.state_id = self.env.ref('base.state_us_27')
        self.contract.write({
            'wage': 10000,
            'schedule_pay': 'semi-monthly',
            'l10n_us_pre_retirement_amount': 10.0,
            'l10n_us_pre_retirement_type': 'percent',
            'l10n_us_health_benefits_medical': 10.0,
            'l10n_us_health_benefits_dental': 10.0,
            'l10n_us_health_benefits_vision': 10.0,
            'l10n_us_health_benefits_hsa': 10.0,
        })
        self.employee.write({
            'l10n_us_w4_allowances_count': 0,
            'l10n_us_state_filing_status': 'ny_status_1',
            'l10n_us_filing_status': 'single',
        })

        payslip = self._generate_payslip(datetime.date(2023, 4, 1), datetime.date(2023, 4, 15))
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 10000.0,
            'GROSS': 10000.0,
            '401K': -1000.0,
            'DENTAL': -10.0,
            'MEDICAL': -10.0,
            'VISION': -10.0,
            'MEDICALHSA': -10.0,
            'TAXABLE': 8960.0,
            'FIT': -1800.53,
            'MEDICARE': -144.42,
            'MEDICAREADD': 0,
            'SST': -617.52,
            'NYINCOMETAX': -545.04,
            'NYSDITAX': -1.3,
            'NYPFLTAX': -45.5,
            'COMPANYFUTA': 420.0,
            'COMPANYMEDICARE': 144.42,
            'COMPANYSOCIAL': 617.52,
            'COMPANYSUI': 313.0,
            'COMPANYNYREEMPLOYMENT': 7.5,
            'NET': 5805.68,
        }
        self._validate_payslip(payslip, payslip_results)
