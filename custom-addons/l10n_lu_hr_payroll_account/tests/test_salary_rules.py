# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='lu'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.lu_company = cls.env.ref('l10n_lu.demo_company_lu')

        cls.env.user.company_ids |= cls.lu_company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.lu_company.ids))

        cls.work_contact = cls.env['res.partner'].create({
            'name': 'LU Employee',
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
                ("0", 13.0, 18.0, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 13.0, 18.0, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 13.0, 18.0, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 13.0, 18.0, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 13.0, 17.0, "afternoon"),
            ]],
        }])

        cls.lu_company.write({
            'resource_calendar_id': cls.resource_calendar.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'LU Employee',
            'address_id': cls.work_contact.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.lu').id,
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': "LU Employee's contract",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.env.company.id,
            'structure_type_id': cls.env.ref('l10n_lu_hr_payroll.structure_type_employee_lux').id,
            'date_start': date(2016, 1, 1),
            'wage': 4000,
            'state': "open",
            'l10n_lu_meal_voucher_amount': 50.4,
            'work_time_rate': 1.0,
        })

    @classmethod
    def _generate_payslip(cls, date_from, date_to, struct_id=False, input_ids=False):
        work_entries = cls.contract.generate_work_entries(date_from, date_to)
        payslip = cls.env['hr.payslip'].create([{
            'name': "Test Payslip",
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'company_id': cls.env.company.id,
            'struct_id': struct_id or cls.env.ref('l10n_lu_hr_payroll.hr_payroll_structure_lux_employee_salary').id,
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
            error.extend([
                "Payslip Actual Values: ",
                "        {",
            ])
            for line in payslip.line_ids:
                error.append("            '%s': %s," % (line.code, line_values[line.code][payslip.id]['total']))
            error.append("        }")
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def test_basic_payslip_1(self):
        self.contract.wage = 1000.0
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {
            'BASIC': 1000.0,
            'BIK_TRANSPORT_NO_VAT': 0.0,
            'BIK_TRANSPORT_VAT': 0.0,
            'T_GROSS': 1000.0,
            'MEAL_VOUCHERS': 50.4,
            'GROSS': 1050.4,
            'HEALTH_FUND': -28.0,
            'SICK_FUND': -2.5,
            'RETIREMENT_FUND': -80.0,
            'DEP_INS': -5.0,
            'TAXES_TOTAL': 110.5,
            'TRANS_FEES': 0.0,
            'ALW_TOTAL': 0.0,
            'TAXABLE': 934.9,
            'TAXES': 0.0,
            'CISSM': 0.0,
            'TAX_CREDIT': 50.0,
            'NET': 984.9,
            'MEAL_VOUCHERS.2': -50.4,
            'BIK_TRANSPORT_NO_VAT.2': 0.0,
            'BIK_TRANSPORT_VAT.2': 0.0,
            'BIK_VARIOUS.2': 0.0,
            'NET_TO_PAY': 934.5,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_basic_payslip_2(self):
        self.contract.wage = 2000.0
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {
            'BASIC': 2000.0,
            'BIK_TRANSPORT_NO_VAT': 0.0,
            'BIK_TRANSPORT_VAT': 0.0,
            'T_GROSS': 2000.0,
            'MEAL_VOUCHERS': 50.4,
            'GROSS': 2050.4,
            'HEALTH_FUND': -56.0,
            'SICK_FUND': -5.0,
            'RETIREMENT_FUND': -160.0,
            'DEP_INS': -19.0,
            'TAXES_TOTAL': 221.0,
            'TRANS_FEES': 0.0,
            'ALW_TOTAL': 0.0,
            'TAXABLE': 1810.4,
            'TAXES': -69.8,
            'CISSM': 70.0,
            'TAX_CREDIT': 50.0,
            'NET': 1860.6,
            'MEAL_VOUCHERS.2': -50.4,
            'BIK_TRANSPORT_NO_VAT.2': 0.0,
            'BIK_TRANSPORT_VAT.2': 0.0,
            'BIK_VARIOUS.2': 0.0,
            'NET_TO_PAY': 1810.2,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_basic_payslip_3(self):
        self.contract.wage = 3000.0
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {
            'BASIC': 3000.0,
            'BIK_TRANSPORT_NO_VAT': 0.0,
            'BIK_TRANSPORT_VAT': 0.0,
            'T_GROSS': 3000.0,
            'MEAL_VOUCHERS': 50.4,
            'GROSS': 3050.4,
            'HEALTH_FUND': -84.0,
            'SICK_FUND': -7.5,
            'RETIREMENT_FUND': -240.0,
            'DEP_INS': -33.0,
            'TAXES_TOTAL': 331.5,
            'TRANS_FEES': 0.0,
            'ALW_TOTAL': 0.0,
            'TAXABLE': 2685.9,
            'TAXES': -219.2,
            'CISSM': 64.12,
            'TAX_CREDIT': 50.0,
            'NET': 2580.82,
            'MEAL_VOUCHERS.2': -50.4,
            'BIK_TRANSPORT_NO_VAT.2': 0.0,
            'BIK_TRANSPORT_VAT.2': 0.0,
            'BIK_VARIOUS.2': 0.0,
            'NET_TO_PAY': 2530.42,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_basic_payslip_4(self):
        self.contract.wage = 3500.0
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {
            'BASIC': 3500.0,
            'BIK_TRANSPORT_NO_VAT': 0.0,
            'BIK_TRANSPORT_VAT': 0.0,
            'T_GROSS': 3500.0,
            'MEAL_VOUCHERS': 50.4,
            'GROSS': 3550.4,
            'HEALTH_FUND': -98.0,
            'SICK_FUND': -8.75,
            'RETIREMENT_FUND': -280.0,
            'DEP_INS': -40.0,
            'TAXES_TOTAL': 386.75,
            'TRANS_FEES': 0.0,
            'ALW_TOTAL': 0.0,
            'TAXABLE': 3123.65,
            'TAXES': -327.7,
            'CISSM': 5.79,
            'TAX_CREDIT': 53.26,
            'NET': 2854.99,
            'MEAL_VOUCHERS.2': -50.4,
            'BIK_TRANSPORT_NO_VAT.2': 0.0,
            'BIK_TRANSPORT_VAT.2': 0.0,
            'BIK_VARIOUS.2': 0.0,
            'NET_TO_PAY': 2804.59,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_basic_payslip_5(self):
        self.contract.wage = 4000.0
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {
            'BASIC': 4000.0,
            'BIK_TRANSPORT_NO_VAT': 0.0,
            'BIK_TRANSPORT_VAT': 0.0,
            'T_GROSS': 4000.0,
            'MEAL_VOUCHERS': 50.4,
            'GROSS': 4050.4,
            'HEALTH_FUND': -112.0,
            'SICK_FUND': -10.0,
            'RETIREMENT_FUND': -320.0,
            'DEP_INS': -47.0,
            'TAXES_TOTAL': 442.0,
            'TRANS_FEES': 0.0,
            'ALW_TOTAL': 0.0,
            'TAXABLE': 3561.4,
            'TAXES': -459.9,
            'CISSM': 0.0,
            'TAX_CREDIT': 60.76,
            'NET': 3162.25,
            'MEAL_VOUCHERS.2': -50.4,
            'BIK_TRANSPORT_NO_VAT.2': 0.0,
            'BIK_TRANSPORT_VAT.2': 0.0,
            'BIK_VARIOUS.2': 0.0,
            'NET_TO_PAY': 3111.85,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_gratification_payslip(self):
        self.employee.departure_date = date(2024, 1, 31)
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        self.env['hr.payslip.input'].create({
            'payslip_id': payslip.id,
            'input_type_id': self.env.ref('l10n_lu_hr_payroll.input_gratification_lu').id,
            'amount': 2000,
        })
        payslip.compute_sheet()
        payslip_results = {
            'BASIC': 4000.0,
            'BIK_TRANSPORT_NO_VAT': 0.0,
            'BIK_TRANSPORT_VAT': 0.0,
            'T_GROSS': 4000.0,
            'MEAL_VOUCHERS': 50.4,
            'GROSS': 4050.4,
            'HEALTH_FUND': -112.0,
            'SICK_FUND': -10.0,
            'RETIREMENT_FUND': -320.0,
            'DEP_INS': -47.0,
            'TAXES_TOTAL': 442.0,
            'TRANS_FEES': 0.0,
            'ALW_TOTAL': 0.0,
            'TAXABLE': 3561.4,
            'TAXES': -459.9,
            'CISSM': 0.0,
            'TAX_CREDIT': 60.76,
            'BASIC_GRATIFICATION': 2000.0,
            'GRAT_HEALTH_FUND': -56.0,
            'GRAT_RETIREMENT_FUND': -160.0,
            'GROSS_GRATIFICATION': 1780.0,
            'TAX_ON_NON_PERIOD_REVENUE': -685.3,
            'NET_GRATIFICATION': 1094.7,
            'NET': 4256.95,
            'MEAL_VOUCHERS.2': -50.4,
            'BIK_TRANSPORT_NO_VAT.2': 0.0,
            'BIK_TRANSPORT_VAT.2': 0.0,
            'BIK_VARIOUS.2': 0.0,
            'NET_TO_PAY': 4206.55,
        }
        self._validate_payslip(payslip, payslip_results)
