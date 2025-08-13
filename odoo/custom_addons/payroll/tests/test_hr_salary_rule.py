# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestPayslipBase


class TestSalaryRule(TestPayslipBase):
    def setUp(self):
        super().setUp()

        self.Payslip = self.env["hr.payslip"]
        self.Rule = self.env["hr.salary.rule"]

        self.test_rule = self.Rule.create(
            {
                "name": "Test Rule",
                "code": "TEST",
                "category_id": self.categ_alw.id,
                "sequence": 6,
                "amount_select": "code",
                "amount_python_compute": "result = 0",
            }
        )
        self.developer_pay_structure.write({"rule_ids": [(4, self.test_rule.id)]})

        self.parent_test_rule = self.Rule.create(
            {
                "name": "Parent Test Rule",
                "code": "PARENT_TEST",
                "category_id": self.categ_alw.id,
                "sequence": 6,
                "parent_rule_id": self.test_rule.id,
                "amount_select": "code",
                "amount_python_compute": "result = 100",
            }
        )
        self.developer_pay_structure.write(
            {"rule_ids": [(4, self.parent_test_rule.id)]}
        )

        self.child_test_rule = self.Rule.create(
            {
                "name": "Child Test Rule",
                "code": "CHILD_TEST",
                "category_id": self.categ_alw.id,
                "sequence": 7,
                "parent_rule_id": self.test_rule.id,
                "amount_select": "code",
                "amount_python_compute": "result = 100",
            }
        )

    def test_python_code_return_values(self):
        self.test_rule.amount_python_compute = (
            "result_rate = 0\n" "result_qty = 0\n" "result = 0\n"
        )

        # Open contracts
        cc = self.env["hr.contract"].search([("employee_id", "=", self.richard_emp.id)])
        cc.kanban_state = "done"
        self.env.ref(
            "hr_contract.ir_cron_data_contract_update_state"
        ).method_direct_trigger()

        # Create payslip and compute
        payslip = self.Payslip.create({"employee_id": self.richard_emp.id})
        payslip.onchange_employee()
        payslip.compute_sheet()

        line = payslip.line_ids.filtered(lambda record: record.code == "TEST")
        self.assertEqual(len(line), 1, "I found the Test line")
        self.assertEqual(line.amount, 0.0, "The amount is zero")
        self.assertEqual(line.rate, 0.0, "The rate is zero")
        self.assertEqual(line.quantity, 0.0, "The quantity is zero")
        self.assertEqual(line.code, "TEST", "The code is 'TEST'")

    def test_python_code_result_not_set(self):
        self.test_rule.amount_python_compute = "result = 2"

        # Open contracts
        cc = self.env["hr.contract"].search([("employee_id", "=", self.richard_emp.id)])
        cc.kanban_state = "done"
        self.env.ref(
            "hr_contract.ir_cron_data_contract_update_state"
        ).method_direct_trigger()

        # Create payslip and compute
        payslip = self.Payslip.create({"employee_id": self.richard_emp.id})
        payslip.onchange_employee()
        payslip.compute_sheet()

        line = payslip.line_ids.filtered(lambda record: record.code == "TEST")
        self.assertEqual(len(line), 1, "I found the Test line")
        self.assertEqual(line.amount, 2.0, "The amount is zero")
        self.assertEqual(line.rate, 100.0, "The rate is zero")
        self.assertEqual(line.quantity, 1.0, "The quantity is zero")

    def test_parent_child_order(self):
        # Open contracts
        cc = self.env["hr.contract"].search([("employee_id", "=", self.richard_emp.id)])
        cc.kanban_state = "done"
        self.env.ref(
            "hr_contract.ir_cron_data_contract_update_state"
        ).method_direct_trigger()

        # Compute Payslip
        payslip = self.Payslip.create({"employee_id": self.richard_emp.id})
        payslip.onchange_employee()
        payslip.compute_sheet()

        # Check child test rule calculated without being in the structure
        line = payslip.line_ids.filtered(lambda record: record.code == "CHILD_TEST")
        self.assertEqual(len(line), 1, "Child line founded")

        # Change sequence of child rule to calculate before of the parent rule
        self.child_test_rule.sequence = 5

        # Compute Payslip
        payslip = self.Payslip.create({"employee_id": self.richard_emp.id})
        payslip.onchange_employee()
        payslip.compute_sheet()

        # Child rule should be computed
        line = payslip.line_ids.filtered(lambda record: record.code == "CHILD_TEST")
        self.assertEqual(len(line), 1, "Child line founded")

        # Change the parent rule condition to return False
        self.test_rule.condition_select = "python"
        self.test_rule.condition_python = "result = False"

        # Compute Payslip
        payslip = self.Payslip.create({"employee_id": self.richard_emp.id})
        payslip.onchange_employee()
        payslip.compute_sheet()

        # Parent and child rule should not be calculated even if child rule condition is true # noqa: E501
        parent_line = payslip.line_ids.filtered(
            lambda record: record.code == "PARENT_TEST"
        )
        child_line = payslip.line_ids.filtered(
            lambda record: record.code == "CHILD_TEST"
        )
        self.assertEqual(len(parent_line), 0, "No parent line found")
        self.assertEqual(len(child_line), 0, "No child line found")

    def test_rule_and_category_with_and_without_code(self):
        rule_test_code = self.SalaryRule.create(
            {
                "name": "rule test code",
                "code": "rule_test_code",
                "sequence": 100,
                "amount_select": "code",
                "amount_python_compute": "result = categories.BASIC + HRA",
            }
        )
        category_without_code = self.SalaryRuleCateg.create({"name": "categ no code"})
        rule_without_code = self.SalaryRule.create(
            {
                "name": "rule without code",
                "category_id": category_without_code.id,
                "sequence": 10,
                "amount_select": "code",
                "amount_python_compute": "result = 100",
            }
        )
        rule_without_category = self.SalaryRule.create(
            {
                "name": "rule without category",
                "sequence": 10,
                "amount_select": "code",
                "amount_python_compute": "result = 100",
            }
        )
        structure = self.PayrollStructure.create(
            {
                "name": "test code and id",
                "rule_ids": [
                    (4, self.rule_basic.id),
                    (4, self.rule_hra.id),
                    (4, rule_test_code.id),
                    (4, rule_without_code.id),
                    (4, rule_without_category.id),
                ],
            }
        )
        payslip = self.Payslip.create(
            {
                "employee_id": self.richard_emp.id,
                "contract_id": self.richard_contract.id,
                "struct_id": structure.id,
            }
        )
        payslip.compute_sheet()
        line = payslip.line_ids.filtered(lambda record: record.code == "rule_test_code")
        self.assertEqual(line.total, 7000, "5000 categories.BASIC + 2000 HRA = 7000")
        line = payslip.line_ids.filtered(
            lambda record: record.name == "rule without code"
        )
        self.assertEqual(len(line), 1, "Line found: rule without code")
        line = payslip.line_ids.filtered(
            lambda record: record.name == "rule without category"
        )
        self.assertEqual(len(line), 1, "Line found: rule without category")
