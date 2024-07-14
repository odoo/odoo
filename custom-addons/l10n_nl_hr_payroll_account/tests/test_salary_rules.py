# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


@tagged('post_install_l10n', 'post_install', '-at_install', 'payslips_validation')
class TestPayslipValidation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='nl'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.nl')

        cls.env.user.tz = 'Europe/Amsterdam'

        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 40 Hours/Week",
            'company_id': cls.env.company.id,
            'hours_per_day': 8.0,
            'tz': "Europe/Amsterdam",
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
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.ch').id,
            'km_home_work': 75,
        }])

        cls.contract = cls.env['hr.contract'].create([{
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'structure_type_id': cls.env.ref('l10n_nl_hr_payroll.structure_type_employee_nl').id,
            'date_start': datetime.date(2018, 12, 31),
            'wage': 5000.0,
            'state': "open",
        }])

    @classmethod
    def _generate_payslip(cls, date_from, date_to, struct_id=False):
        work_entries = cls.contract.generate_work_entries(date_from, date_to)
        payslip = cls.env['hr.payslip'].create([{
            'name': "Test Payslip",
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'company_id': cls.env.company.id,
            'struct_id': struct_id or cls.env.ref('l10n_nl_hr_payroll.hr_payroll_structure_nl_employee_salary').id,
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

    def test_regular_payslip_resident(self):
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 5000, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 176.0, places=2)

        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            'AOW': -524.01,
            'Anw': -2.93,
            'Wlz': -282.5,
            'TAXABLE': 4190.57,
            'INCOMETAX': -724.02,
            'Zvw': -323.91,
            'WW': -132.0,
            'WWFund': -35.89,
            'WAO/WIA': -324.38,
            'Whk': -58.26,
            'NET': 3466.55,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_non_resident(self):
        self.employee.is_non_resident = True

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 5000, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 176.0, places=2)

        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            'AOW': -524.01,
            'Anw': -29.27,
            'Wlz': -282.5,
            'TAXABLE': 4164.22,
            'INCOMETAX': -714.29,
            'Zvw': -323.91,
            'WW': -132.0,
            'WWFund': -35.89,
            'WAO/WIA': -324.38,
            'Whk': -58.26,
            'NET': 3449.93,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_30_percent(self):
        self.employee.is_non_resident = True
        self.contract.l10n_nl_30_percent = True

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 5000, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 176.0, places=2)

        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            'AOW': -524.01,
            'Anw': -29.27,
            'Wlz': -282.5,
            'TAXABLE': 2664.22,
            'INCOMETAX': -247.24,
            'Zvw': -236.25,
            'WW': -92.4,
            'WWFund': -26.95,
            'WAO/WIA': -248.85,
            'Whk': -58.26,
            'NET': 3916.98,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_30_percent_low_salary(self):
        self.employee.is_non_resident = True
        self.contract.l10n_nl_30_percent = True
        self.contract.wage = 1500

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1500, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 176.0, places=2)

        payslip_results = {
            'BASIC': 1500.0,
            'GROSS': 1500.0,
            'AOW': -187.95,
            'Anw': -10.5,
            'Wlz': -101.33,
            'TAXABLE': 750.23,
            'INCOMETAX': -69.62,
            'Zvw': -70.88,
            'WW': -27.72,
            'WWFund': -8.09,
            'WAO/WIA': -74.66,
            'Whk': -58.26,
            'NET': 1130.6,
        }
        self._validate_payslip(payslip, payslip_results)
