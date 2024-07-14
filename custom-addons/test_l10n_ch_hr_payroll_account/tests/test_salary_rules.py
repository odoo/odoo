# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests.common import tagged
from odoo.addons.test_l10n_ch_hr_payroll_account.tests.common import TestL10NChHrPayrollAccountCommon
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


@tagged('post_install_l10n', 'post_install', '-at_install', 'ch_payslips_validation')
class TestPayslipValidation(TestL10NChHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ch'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.work_contact = cls.env['res.partner'].create([{
            'name': "Test Employee",
            'company_id': cls.env.company.id,
        }])

        cls.employee = cls.env['hr.employee'].create([{
            'name': "Test Employee",
            'gender': 'female',
            'work_contact_id': cls.work_contact.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.ch').id,
            'km_home_work': 75,
            'l10n_ch_canton': 'FR',
            'l10n_ch_tax_scale': 'A',
            'lang': 'en_US',
        }])

        cls.contract = cls.env['hr.contract'].create([{
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar_40_hours_per_week.id,
            'company_id': cls.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'structure_type_id': cls.env.ref('l10n_ch_hr_payroll.structure_type_employee_ch').id,
            'date_start': datetime.date(2018, 12, 31),
            'wage': 14000.0,
            'state': "open",
            'l10n_ch_social_insurance_id': cls.social_insurance.id,
            'l10n_ch_accident_insurance_line_id': cls.accident_insurance.line_ids.id,
            'l10n_ch_additional_accident_insurance_line_ids': [(4, cls.additional_accident_insurance.line_ids.id)],
            'l10n_ch_sickness_insurance_line_ids': [(4, cls.sickness_insurance.line_ids.id)],
            'l10n_ch_lpp_insurance_id': cls.lpp_insurance.id,
            'l10n_ch_compensation_fund_id': cls.compensation_fund.id,
            'l10n_ch_thirteen_month': True,
        }])

    @classmethod
    def _generate_payslip(cls, date_from, date_to, struct_id=False):
        work_entries = cls.contract.generate_work_entries(date_from, date_to)
        payslip = cls.env['hr.payslip'].create([{
            'name': "Test Payslip",
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'company_id': cls.env.company.id,
            'struct_id': struct_id or cls.env.ref('l10n_ch_hr_payroll.hr_payroll_structure_ch_employee_salary').id,
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

    def test_001_regular_payslip(self):
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 14000, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 176.0, places=2)

        payslip_results = {
            'BASIC': 14000.0,
            '13THMONTHPROVISION': 1166.67,
            'GROSS': 14000.0,
            'AVSSALARY': 14000.0,
            'AVS': -742.0,
            'AVS.COMP': 742.0,
            'ACSALARY': 12350.0,
            'AC': -135.85,
            'AC.COMP': 135.85,
            'ACCSALARY': 1650.0,
            'ACC': -8.25,
            'ACC.COMP': 0,
            'AANPSALARY': 12350.0,
            'AANP': -72.12,
            'AAP.COMP': 123.5,
            'AANP.COMP': 82.13,
            'LAACSALARY': 12350.0,
            'LAAC': -123.5,
            'LAAC.COMP': 123.5,
            'IJMSALARY': 12350.0,
            'IJM': -61.75,
            'IJM.COMP': 61.75,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -58.94,
            'NET': 12797.59,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_002_ac_low_salary(self):
        self.contract.write({
            'wage': 10000,
            'l10n_ch_thirteen_month': False,
        })

        for month in range(1, 13):
            payslip = self._generate_payslip(
                datetime.date(2023, month, 1),
                datetime.date(2023, month, 1) + relativedelta(day=31))

            self.assertEqual(len(payslip.worked_days_line_ids), 1)
            self.assertEqual(len(payslip.input_line_ids), 0)

            payslip_results = {
                'BASIC': 10000.0,
                'GROSS': 10000.0,
                'AVSSALARY': 10000.0,
                'AVS': -530.0,
                'AVS.COMP': 530.0,
                'ACSALARY': 10000.0,
                'AC': -110.0,
                'AC.COMP': 110.0,
                'ACCSALARY': 0,
                'ACC': 0,
                'ACC.COMP': 0,
                'AANPSALARY': 10000.0,
                'AANP': -58.4,
                'AAP.COMP': 100.0,
                'AANP.COMP': 66.5,
                'LAACSALARY': 10000.0,
                'LAAC': -100.0,
                'LAAC.COMP': 100.0,
                'IJMSALARY': 10000.0,
                'IJM': -50.0,
                'IJM.COMP': 50.0,
                'LPP': 0,
                'LPP.COMP': 0,
                'IS': 0,
                'CAF': -42.1,
                'NET': 9109.5,
            }
            self._validate_payslip(payslip, payslip_results)
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_003_ac_high_salary(self):
        self.contract.write({
            'wage': 20000,
            'l10n_ch_thirteen_month': False,
        })

        for month in range(1, 13):
            payslip = self._generate_payslip(
                datetime.date(2023, month, 1),
                datetime.date(2023, month, 1) + relativedelta(day=31))

            self.assertEqual(len(payslip.worked_days_line_ids), 1)
            self.assertEqual(len(payslip.input_line_ids), 0)

            payslip_results = {
                'BASIC': 20000.0,
                'GROSS': 20000.0,
                'AVSSALARY': 20000.0,
                'AVS': -1060.0,
                'AVS.COMP': 1060.0,
                'ACSALARY': 12350.0,
                'AC': -135.85,
                'AC.COMP': 135.85,
                'ACCSALARY': 7650.0,
                'ACC': -38.25,
                'ACC.COMP': 0,
                'AANPSALARY': 12350.0,
                'AANP': -72.12,
                'AAP.COMP': 123.5,
                'AANP.COMP': 82.13,
                'LAACSALARY': 12350.0,
                'LAAC': -123.5,
                'LAAC.COMP': 123.5,
                'IJMSALARY': 12350.0,
                'IJM': -61.75,
                'IJM.COMP': 61.75,
                'LPP': 0,
                'LPP.COMP': 0,
                'IS': 0,
                'CAF': -84.2,
                'NET': 18424.33,
            }
            self._validate_payslip(payslip, payslip_results)
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_004_ac_temporary_overlimit(self):
        self.contract.write({
            'wage': 10000,
            'l10n_ch_thirteen_month': False,
        })

        payslip_common_result = {
            'BASIC': 10000.0,
            'GROSS': 10000.0,
            'AVSSALARY': 10000.0,
            'AVS': -530.0,
            'AVS.COMP': 530.0,
            'ACSALARY': 10000.0,
            'AC': -110.0,
            'AC.COMP': 110.0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 10000.0,
            'AANP': -58.4,
            'AAP.COMP': 100.0,
            'AANP.COMP': 66.5,
            'LAACSALARY': 10000.0,
            'LAAC': -100.0,
            'LAAC.COMP': 100.0,
            'IJMSALARY': 10000.0,
            'IJM': -50.0,
            'IJM.COMP': 50.0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -42.1,
            'NET': 9109.5,
        }

        payslip_results = {
            1: {
                'BASIC': 10000.0,
                'BONUS': 5000.0,
                'GROSS': 15000.0,
                'AVSSALARY': 15000.0,
                'AVS': -795.0,
                'AVS.COMP': 795.0,
                'ACSALARY': 12350.0,
                'AC': -135.85,
                'AC.COMP': 135.85,
                'ACCSALARY': 2650.0,
                'ACC': -13.25,
                'ACC.COMP': 0,
                'AANPSALARY': 12350.0,
                'AANP': -72.12,
                'AAP.COMP': 123.5,
                'AANP.COMP': 82.13,
                'LAACSALARY': 12350.0,
                'LAAC': -123.5,
                'LAAC.COMP': 123.5,
                'IJMSALARY': 12350.0,
                'IJM': -61.75,
                'IJM.COMP': 61.75,
                'LPP': 0,
                'LPP.COMP': 0,
                'IS': 0,
                'CAF': -63.15,
                'NET': 13735.38,
            },
            2: {
                'BASIC': 10000.0,
                'GROSS': 10000.0,
                'AVSSALARY': 10000.0,
                'AVS': -530.0,
                'AVS.COMP': 530.0,
                'ACSALARY': 12350.0,
                'AC': -135.85,
                'AC.COMP': 135.85,
                'ACCSALARY': -2350.0,
                'ACC': 11.75,
                'ACC.COMP': 0,
                'AANPSALARY': 12350.0,
                'AANP': -72.12,
                'AAP.COMP': 123.5,
                'AANP.COMP': 82.13,
                'LAACSALARY': 12350.0,
                'LAAC': -123.5,
                'LAAC.COMP': 123.5,
                'IJMSALARY': 12350.0,
                'IJM': -61.75,
                'IJM.COMP': 61.75,
                'LPP': 0,
                'LPP.COMP': 0,
                'IS': 0,
                'CAF': -42.1,
                'NET': 9046.43,
            },
            3: {
                'BASIC': 10000.0,
                'GROSS': 10000.0,
                'AVSSALARY': 10000.0,
                'AVS': -530.0,
                'AVS.COMP': 530.0,
                'ACSALARY': 10300.0,
                'AC': -113.3,
                'AC.COMP': 113.3,
                'ACCSALARY': -300.0,
                'ACC': 1.5,
                'ACC.COMP': 0,
                'AANPSALARY': 10300.0,
                'AANP': -60.15,
                'AAP.COMP': 103.0,
                'AANP.COMP': 68.5,
                'LAACSALARY': 10300.0,
                'LAAC': -103.0,
                'LAAC.COMP': 103.0,
                'IJMSALARY': 10300.0,
                'IJM': -51.5,
                'IJM.COMP': 51.5,
                'LPP': 0,
                'LPP.COMP': 0,
                'IS': 0,
                'CAF': -42.1,
                'NET': 9101.45,
            },
            4: payslip_common_result,
            5: payslip_common_result,
            6: payslip_common_result,
            7: payslip_common_result,
            8: payslip_common_result,
            9: payslip_common_result,
            10: payslip_common_result,
            11: payslip_common_result,
            12: payslip_common_result,
        }

        self.env['hr.salary.attachment'].create({
            'employee_ids': [(4, self.employee.id)],
            'monthly_amount': 5000,
            'total_amount': 5000,
            'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id,
            'date_start': datetime.date(2023, 1, 1),
            'date_end': datetime.date(2023, 1, 31),
            'description': 'Bonus',
        })

        for month in range(1, 13):
            payslip = self._generate_payslip(
                datetime.date(2023, month, 1),
                datetime.date(2023, month, 1) + relativedelta(day=31))

            self.assertEqual(len(payslip.worked_days_line_ids), 1)
            self.assertEqual(len(payslip.input_line_ids), 1 if payslip.date_from.month == 1 else 0)

            self._validate_payslip(payslip, payslip_results[month])
            payslip.action_payslip_done()
            payslip.action_payslip_paid()

    def test_005_ac_start_middle_year(self):
        self.contract.write({
            'wage': 5000,
            'date_start': datetime.date(2023, 4, 1),
            'l10n_ch_thirteen_month': False,
        })

        payslip_no_salary_result = {
            'BASIC': 0,
            'GROSS': 0,
            'AVSSALARY': 0,
            'AVS': 0,
            'AVS.COMP': 0,
            'ACSALARY': 0,
            'AC': 0,
            'AC.COMP': 0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 0,
            'AANP': 0,
            'AAP.COMP': 0,
            'AANP.COMP': 0,
            'LAACSALARY': 0,
            'LAAC': 0,
            'LAAC.COMP': 0,
            'IJMSALARY': 0,
            'IJM': 0,
            'IJM.COMP': 0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': 0,
            'NET': 0,
        }

        payslip_common_result = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            'AVSSALARY': 5000.0,
            'AVS': -265.0,
            'AVS.COMP': 265.0,
            'ACSALARY': 5000.0,
            'AC': -55.0,
            'AC.COMP': 55.0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 5000.0,
            'AANP': -29.2,
            'AAP.COMP': 50.0,
            'AANP.COMP': 33.25,
            'LAACSALARY': 5000.0,
            'LAAC': -50.0,
            'LAAC.COMP': 50.0,
            'IJMSALARY': 5000.0,
            'IJM': -25.0,
            'IJM.COMP': 25.0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -21.05,
            'NET': 4554.75,
        }

        payslip_results = {
            1: payslip_no_salary_result,
            2: payslip_no_salary_result,
            3: payslip_no_salary_result,
            4: payslip_common_result,
            5: payslip_common_result,
            6: payslip_common_result,
            7: payslip_common_result,
            8: payslip_common_result,
            9: payslip_common_result,
            10: payslip_common_result,
            11: payslip_common_result,
            12: payslip_common_result,
        }

        for month in range(1, 13):
            payslip = self._generate_payslip(
                datetime.date(2023, month, 1),
                datetime.date(2023, month, 1) + relativedelta(day=31))

            self.assertEqual(len(payslip.worked_days_line_ids), 1)
            self.assertEqual(len(payslip.input_line_ids), 0)

            self._validate_payslip(payslip, payslip_results[month])

            if month < 4:
                with self.assertRaises(ValidationError):
                    payslip.action_payslip_done()
                    payslip.action_payslip_paid()
            else:
                payslip.action_payslip_done()
                payslip.action_payslip_paid()

    def test_006_retired_employee(self):
        self.contract.employee_id.birthday = datetime.date(1940, 1, 1)
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        payslip_results = {
            'BASIC': 14000.0,
            '13THMONTHPROVISION': 1166.67,
            'GROSS': 14000.0,
            'AVSSALARY': 14000.0,
            'AVS': -667.8,
            'AVS.COMP': 742.0,
            'ACSALARY': 12350.0,
            'AC': -135.85,
            'AC.COMP': 135.85,
            'ACCSALARY': 1650.0,
            'ACC': -8.25,
            'ACC.COMP': 0,
            'AANPSALARY': 12350.0,
            'AANP': -72.12,
            'AAP.COMP': 123.5,
            'AANP.COMP': 82.13,
            'LAACSALARY': 12350.0,
            'LAAC': -123.5,
            'LAAC.COMP': 123.5,
            'IJMSALARY': 12350.0,
            'IJM': -61.75,
            'IJM.COMP': 61.75,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -58.94,
            'NET': 12871.79,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_007_acc_salary_annualisation(self):
        self.contract.wage = 10000
        self.contract.l10n_ch_thirteen_month = False

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))
        payslip_results = {
            'BASIC': 10000.0,
            'GROSS': 10000.0,
            'AVSSALARY': 10000.0,
            'AVS': -530.0,
            'AVS.COMP': 530.0,
            'ACSALARY': 10000.0,
            'AC': -110.0,
            'AC.COMP': 110.0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 10000.0,
            'AANP': -58.4,
            'AAP.COMP': 100.0,
            'AANP.COMP': 66.5,
            'LAACSALARY': 10000.0,
            'LAAC': -100.0,
            'LAAC.COMP': 100.0,
            'IJMSALARY': 10000.0,
            'IJM': -50.0,
            'IJM.COMP': 50.0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -42.1,
            'NET': 9109.5,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()

        payslip = self._generate_payslip(datetime.date(2023, 2, 1), datetime.date(2023, 2, 28))
        payslip_results = {
            'BASIC': 10000.0,
            'GROSS': 10000.0,
            'AVSSALARY': 10000.0,
            'AVS': -530.0,
            'AVS.COMP': 530.0,
            'ACSALARY': 10000.0,
            'AC': -110.0,
            'AC.COMP': 110.0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 10000.0,
            'AANP': -58.4,
            'AAP.COMP': 100.0,
            'AANP.COMP': 66.5,
            'LAACSALARY': 10000.0,
            'LAAC': -100.0,
            'LAAC.COMP': 100.0,
            'IJMSALARY': 10000.0,
            'IJM': -50.0,
            'IJM.COMP': 50.0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -42.1,
            'NET': 9109.5,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()

        self.env['hr.salary.attachment'].create({
            'employee_ids': [(4, self.employee.id)],
            'monthly_amount': 20000,
            'total_amount': 20000,
            'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_holiday_bonus').id,
            'date_start': datetime.date(2023, 3, 1),
            'date_end': datetime.date(2023, 3, 31),
            'description': 'Bonus',
        })
        payslip = self._generate_payslip(datetime.date(2023, 3, 1), datetime.date(2023, 3, 31))
        payslip_results = {
            'BASIC': 10000.0,
            'BONUS': 20000.0,
            'GROSS': 30000.0,
            'AVSSALARY': 30000.0,
            'AVS': -1590.0,
            'AVS.COMP': 1590.0,
            'ACSALARY': 17050.0,
            'AC': -187.55,
            'AC.COMP': 187.55,
            'ACCSALARY': 12950.0,
            'ACC': -64.75,
            'ACC.COMP': 0,
            'AANPSALARY': 17050.0,
            'AANP': -99.57,
            'AAP.COMP': 170.5,
            'AANP.COMP': 113.38,
            'LAACSALARY': 17050.0,
            'LAAC': -170.5,
            'LAAC.COMP': 170.5,
            'IJMSALARY': 17050.0,
            'IJM': -85.25,
            'IJM.COMP': 85.25,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -126.3,
            'NET': 27676.08,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_008_acc_salary_exceeded_first_month(self):
        self.contract.wage = 15000
        self.contract.l10n_ch_thirteen_month = False

        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))
        payslip_results = {
            'BASIC': 15000.0,
            'GROSS': 15000.0,
            'AVSSALARY': 15000.0,
            'AVS': -795.0,
            'AVS.COMP': 795.0,
            'ACSALARY': 12350.0,
            'AC': -135.85,
            'AC.COMP': 135.85,
            'ACCSALARY': 2650.0,
            'ACC': -13.25,
            'ACC.COMP': 0,
            'AANPSALARY': 12350.0,
            'AANP': -72.12,
            'AAP.COMP': 123.5,
            'AANP.COMP': 82.13,
            'LAACSALARY': 12350.0,
            'LAAC': -123.5,
            'LAAC.COMP': 123.5,
            'IJMSALARY': 12350.0,
            'IJM': -61.75,
            'IJM.COMP': 61.75,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -63.15,
            'NET': 13735.38,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_009_acc_salary_start_may_below(self):
        self.contract.wage = 10000
        self.contract.date_start = datetime.date(2023, 5, 1)
        self.contract.l10n_ch_thirteen_month = False

        payslip = self._generate_payslip(datetime.date(2023, 5, 1), datetime.date(2023, 5, 31))
        payslip_results = {
            'BASIC': 10000.0,
            'GROSS': 10000.0,
            'AVSSALARY': 10000.0,
            'AVS': -530.0,
            'AVS.COMP': 530.0,
            'ACSALARY': 10000.0,
            'AC': -110.0,
            'AC.COMP': 110.0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 10000.0,
            'AANP': -58.4,
            'AAP.COMP': 100.0,
            'AANP.COMP': 66.5,
            'LAACSALARY': 10000.0,
            'LAAC': -100.0,
            'LAAC.COMP': 100.0,
            'IJMSALARY': 10000.0,
            'IJM': -50.0,
            'IJM.COMP': 50.0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -42.1,
            'NET': 9109.5,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()

        payslip = self._generate_payslip(datetime.date(2023, 6, 1), datetime.date(2023, 6, 30))
        payslip_results = {
            'BASIC': 10000.0,
            'GROSS': 10000.0,
            'AVSSALARY': 10000.0,
            'AVS': -530.0,
            'AVS.COMP': 530.0,
            'ACSALARY': 10000.0,
            'AC': -110.0,
            'AC.COMP': 110.0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 10000.0,
            'AANP': -58.4,
            'AAP.COMP': 100.0,
            'AANP.COMP': 66.5,
            'LAACSALARY': 10000.0,
            'LAAC': -100.0,
            'LAAC.COMP': 100.0,
            'IJMSALARY': 10000.0,
            'IJM': -50.0,
            'IJM.COMP': 50.0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -42.1,
            'NET': 9109.5,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_010_acc_salary_start_may_above(self):
        self.contract.wage = 15000
        self.contract.date_start = datetime.date(2023, 5, 1)
        self.contract.l10n_ch_thirteen_month = False

        payslip = self._generate_payslip(datetime.date(2023, 5, 1), datetime.date(2023, 5, 31))
        payslip_results = {
            'BASIC': 15000.0,
            'GROSS': 15000.0,
            'AVSSALARY': 15000.0,
            'AVS': -795.0,
            'AVS.COMP': 795.0,
            'ACSALARY': 12350.0,
            'AC': -135.85,
            'AC.COMP': 135.85,
            'ACCSALARY': 2650.0,
            'ACC': -13.25,
            'ACC.COMP': 0,
            'AANPSALARY': 12350.0,
            'AANP': -72.12,
            'AAP.COMP': 123.5,
            'AANP.COMP': 82.13,
            'LAACSALARY': 12350.0,
            'LAAC': -123.5,
            'LAAC.COMP': 123.5,
            'IJMSALARY': 12350.0,
            'IJM': -61.75,
            'IJM.COMP': 61.75,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -63.15,
            'NET': 13735.38,
        }
        self._validate_payslip(payslip, payslip_results)
        payslip.action_payslip_done()

        payslip = self._generate_payslip(datetime.date(2023, 6, 1), datetime.date(2023, 6, 30))
        payslip_results = {
            'BASIC': 15000.0,
            'GROSS': 15000.0,
            'AVSSALARY': 15000.0,
            'AVS': -795.0,
            'AVS.COMP': 795.0,
            'ACSALARY': 12350.0,
            'AC': -135.85,
            'AC.COMP': 135.85,
            'ACCSALARY': 2650.0,
            'ACC': -13.25,
            'ACC.COMP': 0,
            'AANPSALARY': 12350.0,
            'AANP': -72.12,
            'AAP.COMP': 123.5,
            'AANP.COMP': 82.13,
            'LAACSALARY': 12350.0,
            'LAAC': -123.5,
            'LAAC.COMP': 123.5,
            'IJMSALARY': 12350.0,
            'IJM': -61.75,
            'IJM.COMP': 61.75,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -63.15,
            'NET': 13735.38,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_011_indemnities(self):
        self.contract.wage = 4000
        self.contract.l10n_ch_thirteen_month = False

        self.env['hr.salary.attachment'].create({
            'employee_ids': [(4, self.employee.id)],
            'monthly_amount': 3000,
            'total_amount': 3000,
            'deduction_type_id': self.env.ref('l10n_ch_hr_payroll.hr_salary_attachment_type_indemnity_accident').id,
            'date_start': datetime.date(2023, 1, 1),
            'date_end': datetime.date(2023, 1, 31),
            'description': 'Accident Indemnity',
        })
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))
        payslip_results = {
            'BASIC': 4000.0,
            'INDACC': -3000.0,
            'GROSS': 1000.0,
            'AVSSALARY': 1000.0,
            'AVS': -53.0,
            'AVS.COMP': 53.0,
            'ACSALARY': 1000.0,
            'AC': -11.0,
            'AC.COMP': 11.0,
            'ACCSALARY': 0,
            'ACC': 0,
            'ACC.COMP': 0,
            'AANPSALARY': 1000.0,
            'AANP': -5.84,
            'AAP.COMP': 10.0,
            'AANP.COMP': 6.65,
            'LAACSALARY': 1000.0,
            'LAAC': -10.0,
            'LAAC.COMP': 10.0,
            'IJMSALARY': 1000.0,
            'IJM': -5.0,
            'IJM.COMP': 5.0,
            'LPP': 0,
            'LPP.COMP': 0,
            'IS': 0,
            'CAF': -4.21,
            'INDACC2': 3000.0,
            'NET': 3910.95,
        }
        self._validate_payslip(payslip, payslip_results)
