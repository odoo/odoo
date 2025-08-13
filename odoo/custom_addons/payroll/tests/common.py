# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.fields import Date
from odoo.tests.common import TransactionCase


class TestPayslipBase(TransactionCase):
    def setUp(self):
        super().setUp()

        self.CalendarAttendance = self.env["resource.calendar.attendance"]
        self.Contract = self.env["hr.contract"]
        self.ContributionRegister = self.env["hr.contribution.register"]
        self.Department = self.env["hr.department"]
        self.PayrollStructure = self.env["hr.payroll.structure"]
        self.Payslip = self.env["hr.payslip"]
        self.ResourceCalendar = self.env["resource.calendar"]
        self.RuleInput = self.env["hr.rule.input"]
        self.SalaryRule = self.env["hr.salary.rule"]
        self.SalaryRuleCateg = self.env["hr.salary.rule.category"]

        # Departments
        #
        self.dept_rd = self.Department.create({"name": "Research & Development"})
        self.dept_sales = self.Department.create({"name": "Sales"})

        # Salary Rule Categories
        #
        self.categ_basic = self.SalaryRuleCateg.create(
            {
                "name": "Basic",
                "code": "BASIC",
            }
        )
        self.categ_alw = self.SalaryRuleCateg.create(
            {
                "name": "Allowance",
                "code": "ALW",
            }
        )
        self.categ_gross = self.SalaryRuleCateg.create(
            {
                "name": "Gross",
                "code": "GROSS",
            }
        )
        self.categ_ded = self.SalaryRuleCateg.create(
            {
                "name": "Deduction",
                "code": "DED",
            }
        )
        self.categ_net = self.SalaryRuleCateg.create(
            {
                "name": "NET",
                "code": "NET",
            }
        )

        #
        # Salary Rules
        #

        # Earnings
        #
        self.rule_basic = self.SalaryRule.create(
            {
                "name": "Basic Salary",
                "code": "BASIC",
                "sequence": 1,
                "category_id": self.categ_basic.id,
                "condition_select": "none",
                "amount_select": "code",
                "amount_python_compute": "result = contract.wage",
            }
        )
        self.rule_hra = self.SalaryRule.create(
            {
                "name": "House Rent Allowance",
                "code": "HRA",
                "sequence": 5,
                "category_id": self.categ_alw.id,
                "condition_select": "none",
                "amount_select": "percentage",
                "amount_percentage": 40.0,
                "amount_percentage_base": "contract.wage",
            }
        )
        self.rule_meal = self.SalaryRule.create(
            {
                "name": "Meal Voucher",
                "code": "MA",
                "sequence": 16,
                "category_id": self.categ_alw.id,
                "condition_select": "none",
                "amount_select": "fix",
                "amount_fix": 10.0,
                "quantity": "worked_days.WORK100 and worked_days.WORK100.number_of_days",  # noqa: E501
            }
        )
        self.rule_commission = self.SalaryRule.create(
            {
                "name": "Get 1% of sales",
                "code": "SALE",
                "sequence": 17,
                "category_id": self.categ_alw.id,
                "condition_select": "none",
                "amount_select": "code",
                "amount_python_compute": "result = "
                "(inputs.SALEURO and inputs.SALEURO.amount) * 0.01",
            }
        )
        self.RuleInput.create(
            {
                "name": "Sales to Europe",
                "code": "SALEURO",
                "input_id": self.rule_commission.id,
            }
        )

        # Gross
        #
        self.rule_gross = self.SalaryRule.create(
            {
                "name": "Gross",
                "code": "GROSS",
                "sequence": 100,
                "category_id": self.categ_gross.id,
                "condition_select": "none",
                "amount_select": "code",
                "amount_python_compute": "result = categories.BASIC + categories.ALW",
            }
        )

        # Deductions
        #
        self.rule_proftax = self.SalaryRule.create(
            {
                "name": "Professional Tax",
                "code": "PT",
                "sequence": 150,
                "category_id": self.categ_ded.id,
                "condition_select": "none",
                "amount_select": "fix",
                "amount_fix": -200.0,
            }
        )

        # Net
        #
        self.rule_net = self.SalaryRule.create(
            {
                "name": "Net",
                "code": "NET",
                "sequence": 200,
                "category_id": self.categ_net.id,
                "condition_select": "none",
                "amount_select": "code",
                "amount_python_compute": "result = categories.BASIC "
                "+ categories.ALW + categories.DED",
            }
        )

        # Test Child Line
        #
        self.rule_child = self.SalaryRule.create(
            {
                "name": "Net Child Rule",
                "code": "NET_CHILD",
                "sequence": 190,
                "category_id": self.categ_net.id,
                "parent_rule_id": self.rule_net.id,
                "condition_select": "none",
                "amount_select": "code",
                "amount_python_compute": "result = categories.BASIC "
                "+ categories.ALW + categories.DED",
            }
        )

        # Contribution Registers
        #
        self.register_hra = self.ContributionRegister.create(
            {"name": "House Rent Allowance"}
        )

        # I create a new employee "Richard"
        self.richard_emp = self.env["hr.employee"].create(
            {
                "name": "Richard",
                "gender": "male",
                "birthday": "1984-05-01",
                "country_id": self.ref("base.be"),
                "department_id": self.dept_rd.id,
            }
        )

        # I create a salary structure for "Software Developer"
        self.developer_pay_structure = self.PayrollStructure.create(
            {
                "name": "Salary Structure for Software Developer",
                "code": "SD",
                "company_id": self.ref("base.main_company"),
                "rule_ids": [
                    (4, self.rule_hra.id),
                    (4, self.rule_proftax.id),
                    (4, self.rule_meal.id),
                    (4, self.rule_commission.id),
                    (4, self.rule_basic.id),
                    (4, self.rule_gross.id),
                    (4, self.rule_net.id),
                ],
            }
        )

        # I create a contract for "Richard"
        self.richard_contract = self.Contract.create(
            {
                "date_start": Date.today(),
                "name": "Contract for Richard",
                "wage": 5000.0,
                "employee_id": self.richard_emp.id,
                "struct_id": self.developer_pay_structure.id,
                "kanban_state": "done",
            }
        )

        # I create a salary structure for "Sales Person"
        self.sales_pay_structure = self.PayrollStructure.create(
            {
                "name": "Salary Structure for Sales Person",
                "code": "SP",
                "company_id": self.ref("base.main_company"),
                "rule_ids": [
                    (4, self.rule_commission.id),
                    (4, self.rule_basic.id),
                    (4, self.rule_gross.id),
                    (4, self.rule_net.id),
                ],
            }
        )

        # I create another employee Sally and a contract for her
        self.sally = self.env["hr.employee"].create(
            {
                "name": "Sally",
                "department_id": self.dept_sales.id,
            }
        )
        self.Contract.create(
            {
                "date_start": Date.today().strftime("%Y-%m-1"),
                "name": "Contract for Sally",
                "wage": 6500.0,
                "employee_id": self.sally.id,
                "struct_id": self.sales_pay_structure.id,
                "kanban_state": "done",
            }
        )

    def apply_contract_cron(self):
        self.env.ref(
            "hr_contract.ir_cron_data_contract_update_state"
        ).method_direct_trigger()
