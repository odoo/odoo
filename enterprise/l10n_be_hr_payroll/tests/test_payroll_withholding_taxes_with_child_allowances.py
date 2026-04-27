# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'payroll_withholding_taxes_with_child_allowances')
class TestPayrollWithholdingTaxesWithChildAllowances(TestPayrollCommon):
    """
    This class includes test cases for Belgian Payroll withholding taxes computation.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("hr_payroll.BASIC").code = "BASIC"
        cls.env.ref("hr_payroll.GROSS").code = "GROSS"
        cls.env.ref("hr_payroll.ALW").code = "ALW"

    def test_compute_13th_month_withholding_taxes_without_children(self):
        """
        Test Case:
        The calculation of Employee 13th Month Withholding taxes for an employee :
        Employee has 0 children
        Employee wage_on_payroll 2500

        Computation:
        basic = gross = monthly_revenue = wage_on_payroll
        13th_month_ONSS = gross * 13.07% = 326.75
        taxable_salary = (basic - 13th_month_ONSS) = 2500 - 326.75 = 2173.25

        monthly_ONSS = monthly_revenue * 13.07% = 326.75
        yearly_revenue = (monthly_revenue - monthly_ONSS) * 12 = 26079

        tax_rate (based on yearly_revenue) = 40.38%
        withholding_tax_amount = taxable_salary * tax_rate = 877.56
        The employee is not eligible for exoneration nor tax-rate reduction.
        """
        self.employee_withholding_taxes_payslip['struct_id'] = self.env['hr.payroll.structure'].search(
            [('name', '=', 'CP200: Employees 13th Month')]
        )
        date_from = date(2024, 12, 1)
        date_to = date_from + relativedelta(months=+1, day=1, days=-1)
        self.employee_withholding_taxes_contracts.generate_work_entries(date_from, date_to)
        self.employee_withholding_taxes_payslip['date_from'] = date_from
        self.employee_withholding_taxes_payslip['date_to'] = date_to
        self.employee_withholding_taxes_payslip.compute_sheet()

        withholding_tax_line = self.employee_withholding_taxes_payslip.line_ids.filtered(
            lambda line: line.name == 'Withholding Tax'
        )

        self.assertAlmostEqual(withholding_tax_line.amount, -877.56)

    def test_compute_13th_month_withholding_taxes_with_3_children(self):
        """
        Test Case:
        The calculation of Employee 13th Month Withholding taxes for an employee :
        Employee has 3 children
        Employee wage_on_payroll 2500

        Computation:
        basic = gross = monthly_revenue = wage_on_payroll
        13th_month_ONSS = gross * 13.07% = 326.75
        taxable_salary = (basic - 13th_month_ONSS) = 2500 - 326.75 = 2173.25

        monthly_ONSS = monthly_revenue * 13.07% = 326.75
        yearly_revenue = (monthly_revenue - monthly_ONSS) * 12 = 26079
        exoneration limit (based on number of children and yearly_revenue) = 27430
        yearly_revenue (after exoneration) = 26079 - (27430 - 26079) = 24728

        tax_rate (based on yearly_revenue) = 38.36%
        withholding_tax_amount = taxable_salary * tax_rate = 833.6587
        tax_reduction (based on number of children and yearly_revenue) = 35%
        withholding_tax_amount after reduction = 833.6587 * (1 - 0.35) = 541.878155 = 541.88
        """
        self.employee_withholding_taxes.children = 3

        self.employee_withholding_taxes_payslip['struct_id'] = self.env['hr.payroll.structure'].search(
            [('name', '=', 'CP200: Employees 13th Month')]
        )
        date_from = date(2024, 12, 1)
        date_to = date_from + relativedelta(months=+1, day=1, days=-1)
        self.employee_withholding_taxes_contracts.generate_work_entries(date_from, date_to)
        self.employee_withholding_taxes_payslip['date_from'] = date_from
        self.employee_withholding_taxes_payslip['date_to'] = date_to

        self.employee_withholding_taxes_payslip.compute_sheet()

        withholding_tax_line = self.employee_withholding_taxes_payslip.line_ids.filtered(
            lambda line: line.name == 'Withholding Tax'
        )

        self.assertAlmostEqual(withholding_tax_line.amount, -541.88)

    def test_compute_double_holiday_withholding_taxes_with_3_children(self):
        """
        Test Case:
        The calculation of Employee 13th Month Withholding taxes for an employee :
        Employee has 3 children
        Employee wage_on_payroll 2500

        Computation:
        basic = wage_on_payroll * 0.92 = 2300 (For double holiday pay, the basic salary is 92% of the wage)
        gross = wage_on_payroll * 0.85 = 2125 (For double holiday pay, the gross is 0.85% of the wage)
        double_holiday_pay_ONSS = gross * 0.1307 = 277.7375
        taxable_salary = (basic - double_holiday_pay_ONSS) = 2300 - 277.7375 =  2022.2625

        monthly_revenue = wage_on_payroll
        monthly_ONSS = monthly_revenue * 13.07% = 326.75
        yearly_revenue = (monthly_revenue - monthly_ONSS) * 12 = 26079
        exoneration limit (based on number of children and yearly_revenue) = 27430
        yearly_revenue (after exoneration) = 26079 - (27430 - 26079) = 24728

        tax_rate (based on yearly_revenue) = 34.33%
        withholding_tax_amount = taxable_salary * tax_rate = 694.2427163
        tax_reduction (based on number of children and yearly_revenue) = 35%
        withholding_tax_amount after reduction = 694.2427163 * (1 - 0.35) = 451.2577656 = 451.26
        """
        self.employee_withholding_taxes.children = 3
        date_from = date(date.today().year, 1, 1)
        date_to = date_from + relativedelta(months=+1, day=1, days=-1)
        self.employee_withholding_taxes_payslip['date_from'] = date_from
        self.employee_withholding_taxes_payslip['date_to'] = date_to
        self.employee_withholding_taxes_payslip['struct_id'] = self.env['hr.payroll.structure'].search(
            [('name', '=', 'CP200: Employees Double Holidays')]
        )

        self.employee_withholding_taxes_payslip.compute_sheet()

        withholding_tax_line = self.employee_withholding_taxes_payslip.line_ids.filtered(
            lambda line: line.name == 'Withholding Tax'
        )

        self.assertAlmostEqual(withholding_tax_line.amount, -411.43)

    def test_compute_termination_fees_withholding_taxes_with_3_children_after_2024(self):
        """
        Test Case:
        The calculation of Employee 13th Month Withholding taxes for an employee :
        Employee has 3 children
        Employee wage_on_payroll 2500
        Employee notice_duration 1 month

        Computation:
        gross_yearly_salary = wage_on_payroll * 12.92 = 32300
        annual_salary_revalued = gross_yearly_salary = 32300
        basic = (annual_salary_revalued / 12) * notice_period in months = 2691.666667
        termination_fees_ONSS = basic * 0.1307 = 351.8008338
        taxable_salary = (basic - termination_fees_ONSS) = 2691.666667 - 351.8008338 =  2339.865834

        monthly_revenue = wage_on_payroll
        monthly_ONSS = monthly_revenue * 13.07% = 326.75
        yearly_revenue = (monthly_revenue - monthly_ONSS) * 12 = 26079
        exoneration limit (based on number of children and yearly_revenue) = 27430
        yearly_revenue (after exoneration) = 26079 - (27430 - 26079) = 24728

        tax_rate (based on yearly_revenue) = 19.17%
        withholding_tax_amount = taxable_salary * tax_rate = 448.5522804
        tax-rate reduction doesn't apply on termination_fees_withholding_taxes
        """
        self.employee_withholding_taxes.children = 3

        date_from = date(2024, 1, 1)
        date_to = date_from + relativedelta(months=+1, day=1, days=-1)
        self.employee_withholding_taxes_payslip['date_from'] = date_from
        self.employee_withholding_taxes_payslip['date_to'] = date_to
        self.employee_withholding_taxes_payslip['struct_id'] = self.env['hr.payroll.structure'].search(
            [('name', '=', 'CP200: Employees Termination Fees')]
        )

        notice_period_in_month = self.env['hr.payslip.input'].create({
            'payslip_id': self.employee_withholding_taxes_payslip.id,
            'input_type_id': self.env['hr.payslip.input.type'].search([('name', '=', 'Duration in month')]).id,
            'amount': 1,
        })
        self.employee_withholding_taxes_payslip['input_line_ids'] = notice_period_in_month
        self.employee_withholding_taxes_payslip.compute_sheet()

        withholding_tax_line = self.employee_withholding_taxes_payslip.line_ids.filtered(
            lambda line: line.name == 'Withholding Tax'
        )

        self.assertAlmostEqual(withholding_tax_line.amount, -448.55)

    def test_compute_termination_fees_withholding_taxes_with_3_children_before_2024(self):
        """
        Test Case:
        The calculation of Employee 13th Month Withholding taxes for an employee :
        Employee has 3 children
        Employee wage_on_payroll 2500
        Employee notice_duration 1 month

        Computation:
        gross_yearly_salary = wage_on_payroll * 12.92 = 32300
        annual_salary_revalued = gross_yearly_salary = 32300
        basic = (annual_salary_revalued / 12) * notice_period in months = 2691.666667
        termination_fees_ONSS = basic * 0.1307 = 351.8008338
        taxable_salary = (basic - termination_fees_ONSS) = 2691.666667 - 351.8008338 =  2339.865834

        yearly_revenue = taxable_salary * 12 = 28078.39001
        expense_deduction = 5510.0
        yearly_revenue after expense deduction = 28078.39001 - 5510.0 = 22568.39001

        basic_bareme (taxes on yearly_revenue) = 15170 * 0.2675 + (22568.39001 - 15170) * 0.428 = 7224.485924
        deduct_single_with_income = 2573.35
        basic_bareme after deduct_single_with_income = 7224.485924 - 2573.35 = 4651.135923
        withholding_tax = basic_bareme / 12 = 4651.135923 / 12 = 387.59

        # Other Reductions
        disabled_dependent_deduction = 45
        child_allowances = 326.0
        withholding_tax after reductions = 387.59 - 326 - 45 = 16.59

        """
        self.employee_withholding_taxes.children = 3

        self.employee_withholding_taxes_payslip['struct_id'] = self.env['hr.payroll.structure'].search(
            [('name', '=', 'CP200: Employees Termination Fees')]
        )
        date_from = date(2023, 1, 1)
        date_to = date_from + relativedelta(months=+1, day=1, days=-1)
        self.employee_withholding_taxes_payslip['date_from'] = date_from
        self.employee_withholding_taxes_payslip['date_to'] = date_to

        notice_period_in_month = self.env['hr.payslip.input'].create({
            'payslip_id': self.employee_withholding_taxes_payslip.id,
            'input_type_id': self.env['hr.payslip.input.type'].search([('name', '=', 'Duration in month')]).id,
            'amount': 1,
        })
        self.employee_withholding_taxes_payslip['input_line_ids'] = notice_period_in_month
        self.employee_withholding_taxes_payslip.compute_sheet()

        withholding_tax_line = self.employee_withholding_taxes_payslip.line_ids.filtered(
            lambda line: line.name == 'Withholding Tax'
        )

        self.assertAlmostEqual(withholding_tax_line.amount, -16.59)
