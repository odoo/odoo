# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare

@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ma'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.ma')

        cls.address_home_ghofrane = cls.env['res.partner'].create({
            'name': 'Ghofrane',
            'company_id': cls.env.company.id,
        })
        cls.resource_calendar = cls.env['resource.calendar'].create([{
            'name': 'Test Calendar',
            'company_id': cls.env.company.id,
            'hours_per_day': 7.3,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 44,
            'full_time_required_hours': 44,
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
                ("0", 13.0, 18.0, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 18.0, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 12.0, 13.0, "lunch"),
                ("2", 13.0, 18.0, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 18.0, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 17.0, "afternoon"),
            ]],
        }])

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Ghofrane',
            'address_id': cls.address_home_ghofrane.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.ma').id,
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': "Ghofrane's contract",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.env.company.id,
            'structure_type_id': cls.env.ref('l10n_ma_hr_payroll.structure_type_employee_mar').id,
            'date_start': date(2021, 1, 1),
            'wage': 5000.0,
            'state': "open",
        })

    @classmethod
    def _generate_payslip(cls, date_from, date_to, struct_id=False):
        work_entries = cls.contract.generate_work_entries(date_from, date_to)
        payslip = cls.env['hr.payslip'].create([{
            'name': "Test Payslip",
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'company_id': cls.env.company.id,
            'struct_id': struct_id or cls.env.ref('l10n_ma_hr_payroll.hr_payroll_salary_ma_structure_base').id,
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
            error.append("Payslip Actual Values: ")
            error.append("        {")
            for line in payslip.line_ids:
                error.append("            '%s': %s," % (line.code, line_values[line.code][payslip.id]['total']))
            error.append("        }")
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def test_cnss_rule(self):
        payslip = self._generate_payslip(date(2021, 1, 1), date(2021, 1, 31))
        payslip_results = {
            'BASIC': 5000.0,
            'GROSS': 5000.0,
            'E_CNSS': 224.0,
            'JOB_LOSS_ALW': 9.5,
            'E_AMO': 9.5,
            'MEDICAL_ALW': 113.0,
            'CIMR': 150.0,
            'PRO_CONTRIBUTION': 150.0,
            'TOTAL_UT_DED': 656.0,
            'GROSS_TAXABLE': 4344.0,
            'GROSS_INCOME_TAX': 202.13,
            'FAMILY_CHARGE': 0,
            'NET_INCOME_TAX': 202.13,
            'SOCIAL_CONTRIBUTION': 0,
            'NET': 3939.74,
        }
        self._validate_payslip(payslip, payslip_results)

        self.contract.wage = 5600
        payslip = self._generate_payslip(date(2022, 5, 1), date(2022, 5, 31))
        payslip_results = {
            'BASIC': 5600.0,
            'GROSS': 5600.0,
            'E_CNSS': 250.88,
            'JOB_LOSS_ALW': 10.64,
            'E_AMO': 10.64,
            'MEDICAL_ALW': 126.56,
            'CIMR': 168.0,
            'PRO_CONTRIBUTION': 168.0,
            'TOTAL_UT_DED': 734.72,
            'GROSS_TAXABLE': 4865.28,
            'GROSS_INCOME_TAX': 306.39,
            'FAMILY_CHARGE': 0,
            'NET_INCOME_TAX': 306.39,
            'SOCIAL_CONTRIBUTION': 0,
            'NET': 4252.51,
        }
        self._validate_payslip(payslip, payslip_results)

        self.contract.wage = 6000
        payslip = self._generate_payslip(date(2022, 6, 1), date(2022, 6, 30))
        payslip_results = {
            'BASIC': 6000.0,
            'GROSS': 6000.0,
            'E_CNSS': 268.8,
            'JOB_LOSS_ALW': 11.4,
            'E_AMO': 11.4,
            'MEDICAL_ALW': 135.6,
            'CIMR': 180.0,
            'PRO_CONTRIBUTION': 180.0,
            'TOTAL_UT_DED': 787.2,
            'GROSS_TAXABLE': 5212.8,
            'GROSS_INCOME_TAX': 397.17,
            'FAMILY_CHARGE': 0,
            'NET_INCOME_TAX': 397.17,
            'SOCIAL_CONTRIBUTION': 0,
            'NET': 4418.46,
        }
        self._validate_payslip(payslip, payslip_results)

        self.contract.wage = 7500
        payslip = self._generate_payslip(date(2023, 1, 1), date(2023, 1, 31))
        payslip_results = {
            'BASIC': 7500.0,
            'SENIORITY': 0,
            'GROSS': 7500.0,
            'E_CNSS': 268.8,
            'JOB_LOSS_ALW': 14.25,
            'E_AMO': 14.25,
            'MEDICAL_ALW': 169.5,
            'CIMR': 225.0,
            'PRO_CONTRIBUTION': 225.0,
            'TOTAL_UT_DED': 916.8,
            'GROSS_TAXABLE': 6583.2,
            'GROSS_INCOME_TAX': 808.29,
            'FAMILY_CHARGE': 0,
            'NET_INCOME_TAX': 808.29,
            'SOCIAL_CONTRIBUTION': 0,
            'NET': 4966.62,
        }
        self._validate_payslip(payslip, payslip_results)
