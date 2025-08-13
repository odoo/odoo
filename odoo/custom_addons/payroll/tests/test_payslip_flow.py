# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.fields import Date
from odoo.tests import Form
from odoo.tools import test_reports

from .common import TestPayslipBase


class TestPayslipFlow(TestPayslipBase):
    def setUp(self):
        super().setUp()

        self.test_rule = self.SalaryRule.create(
            {
                "name": "Test rule",
                "code": "TEST",
                "category_id": self.categ_alw.id,
                "sequence": 5,
                "amount_select": "code",
                "amount_python_compute": "result = contract.wage",
            }
        )

    def test_00_payslip_flow(self):
        """Testing payslip flow and report printing"""

        # I put all eligible contracts (including Richard's) in an "open" state
        self.apply_contract_cron()

        # I create an employee Payslip
        frm = Form(self.Payslip)
        frm.employee_id = self.richard_emp
        richard_payslip = frm.save()

        payslip_input = self.env["hr.payslip.input"].search(
            [("payslip_id", "=", richard_payslip.id), ("code", "=", "SALEURO")]
        )
        # I assign the amount to Input data
        payslip_input.write({"amount": 5.0})

        # I verify the payslip is in draft state
        self.assertEqual(richard_payslip.state, "draft", "State not changed!")

        # I click on 'Compute Sheet' button on payslip
        richard_payslip.with_context(
            {},
            lang="en_US",
            tz=False,
            active_model="ir.ui.menu",
            department_id=False,
            section_id=False,
            active_ids=[self.ref("payroll.hr_payslip_menu")],
            active_id=self.ref("payroll.hr_payslip_menu"),
        ).compute_sheet()

        # Check child rules shown in table by default
        child_line = richard_payslip.dynamic_filtered_payslip_lines.filtered(
            lambda record: record.code == "NET_CHILD"
        )
        self.assertEqual(
            len(child_line), 1, "Child line found when flag desactivated (default)"
        )

        # Check parent line id value is correct
        parent_line = richard_payslip.dynamic_filtered_payslip_lines.filtered(
            lambda record: record.code == "NET"
        )
        self.assertEqual(
            child_line.parent_line_id.code,
            parent_line.code,
            "Child line parent_id is correct",
        )

        # Check parent line id is False in a rule that have not parent defined
        self.assertEqual(
            len(parent_line.parent_line_id), 0, "The parent line has no parent_line_id"
        )

        # We change child rules show/hide flag
        richard_payslip.hide_child_lines = True

        # Check child rules not shown in table after flag changed
        child_line = richard_payslip.dynamic_filtered_payslip_lines.filtered(
            lambda record: record.code == "NET_CHILD"
        )
        self.assertEqual(
            len(child_line), 0, "The child line is not found when flag activated"
        )

        # Find the 'NET' payslip line and check that it adds up
        # salary + HRA + MA + SALE - PT
        work100 = richard_payslip.worked_days_line_ids.filtered(
            lambda x: x.code == "WORK100"
        )
        line = richard_payslip.line_ids.filtered(lambda record: record.code == "NET")
        self.assertEqual(len(line), 1, "I found the 'NET' line")
        self.assertEqual(
            line[0].amount,
            5000.0 + (0.4 * 5000) + (work100.number_of_days * 10) + 0.05 - 200.0,
            "The 'NET' amount equals salary plus allowances - deductions",
        )

        # Then I click on the 'Confirm' button on payslip
        richard_payslip.action_payslip_done()

        # I verify that the payslip is in done state
        self.assertEqual(richard_payslip.state, "done", "State not changed!")

        # I want to check refund payslip so I click on refund button.
        richard_payslip.refund_sheet()

        # I check on new payslip Credit Note is checked or not.
        payslip_refund = self.env["hr.payslip"].search(
            [
                ("name", "like", "Refund: " + richard_payslip.name),
                ("credit_note", "=", True),
            ]
        )
        self.assertTrue(bool(payslip_refund), "Payslip not refunded!")

        # I want to generate a payslip from Payslip run.
        payslip_run = self.env["hr.payslip.run"].create(
            {
                "date_end": "2011-09-30",
                "date_start": "2011-09-01",
                "name": "Payslip for Employee",
            }
        )

        # I create record for generating the payslip for this Payslip run.
        payslip_employee = self.env["hr.payslip.employees"].create(
            {"employee_ids": [(4, self.richard_emp.id)]}
        )

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

        # I open Contribution Register and from there I print the Payslip Lines report.
        self.env["payslip.lines.contribution.register"].create(
            {"date_from": "2011-09-30", "date_to": "2011-09-01"}
        )

        # I print the payslip report
        data, data_format = self.env.ref(
            "payroll.action_report_payslip"
        )._render_qweb_pdf(
            self.env.ref("payroll.action_report_payslip"), res_ids=richard_payslip.ids
        )

        # I print the payslip details report
        data, data_format = self.env.ref(
            "payroll.payslip_details_report"
        )._render_qweb_pdf(
            self.env.ref("payroll.payslip_details_report"), res_ids=richard_payslip.ids
        )

        # I print the contribution register report
        context = {
            "model": "hr.contribution.register",
            "active_ids": [self.register_hra.id],
        }
        test_reports.try_report_action(
            self.env.cr,
            self.env.uid,
            "action_payslip_lines_contribution_register",
            context=context,
            our_module="payroll",
        )

    def test_contract_qty(self):
        # I set the test rule to detect contract count
        self.test_rule.amount_python_compute = (
            "result = payroll.contracts and payroll.contracts.count or -1.0"
        )
        self.developer_pay_structure.write({"rule_ids": [(4, self.test_rule.id)]})

        # I put all eligible contracts (including Richard's) in an "open" state
        self.apply_contract_cron()

        # I create an employee Payslip and process it
        richard_payslip = self.Payslip.create({"employee_id": self.richard_emp.id})
        richard_payslip.onchange_employee()
        richard_payslip.compute_sheet()

        line = richard_payslip.line_ids.filtered(lambda record: record.code == "TEST")
        self.assertEqual(len(line), 1, "I found the Test line")
        self.assertEqual(
            line[0].amount, 1.0, "The calculated dictionary value 'contracts.qty' is 1"
        )

    def test_compute_multiple_payslips(self):
        self.apply_contract_cron()
        payslips = self.Payslip.create(
            [
                {"employee_id": self.richard_emp.id},
                {"employee_id": self.sally.id},
            ]
        )
        payslips.onchange_employee()
        self.assertEqual(len(payslips.ids), 2, "We have multiple payslips")

        payslips.compute_sheet()
        self.assertTrue(
            payslips[0].number, "The first payslip as been assigned a number"
        )
        self.assertTrue(
            payslips[1].number, "The second payslip as been assigned a number"
        )

    def test_get_contracts_singleton(self):
        payslip = self.Payslip.create({"employee_id": self.sally.id})
        contracts = payslip._get_employee_contracts()
        self.assertFalse(contracts, "No currently open contracts for the employee")

        self.apply_contract_cron()
        contracts = payslip._get_employee_contracts()
        self.assertEqual(
            len(contracts), 1, "There is one open contract for the employee"
        )

        self.sally.contract_id.date_end = (Date.today() - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        self.Contract.create(
            {
                "name": "Second contract for Sally",
                "employee_id": self.sally.id,
                "date_start": Date.today().strftime("%Y-%m-%d"),
                "struct_id": self.sales_pay_structure.id,
                "wage": 6500.00,
                "state": "open",
                "kanban_state": "done",
            }
        )
        contracts = payslip._get_employee_contracts()
        self.assertEqual(
            len(contracts), 1, "There is one open contract for the employee"
        )

    def test_get_contracts_multiple(self):
        self.sally.contract_ids[0].date_end = (
            Date.today() - timedelta(days=1)
        ).strftime("%Y-%m-%d")

        self.Contract.create(
            {
                "name": "Second contract for Sally",
                "employee_id": self.sally.id,
                "date_start": Date.today().strftime("%Y-%m-%d"),
                "struct_id": self.sales_pay_structure.id,
                "wage": 6500.00,
                "state": "open",
                "kanban_state": "done",
            }
        )
        self.apply_contract_cron()

        payslips = self.Payslip.create(
            [
                {"employee_id": self.richard_emp.id},
                {"employee_id": self.sally.id},
            ]
        )
        contracts = payslips._get_employee_contracts()
        self.assertEqual(
            len(contracts), 3, "There are 3 open contracts in the payslips"
        )

    def test_compute_sheet_no_valid_contract(self):
        frm = Form(self.Payslip)
        frm.employee_id = self.richard_emp
        payslip = frm.save()
        payslip.compute_sheet()
        self.assertEqual(
            len(payslip.line_ids),
            0,
            "There are no lines because there are no valid contracts",
        )

    def _get_developer_rules(self):
        developer_rules = self.SalaryRule
        developer_rules |= self.rule_basic
        developer_rules |= self.rule_hra
        developer_rules |= self.rule_meal
        developer_rules |= self.rule_commission
        developer_rules |= self.rule_gross
        developer_rules |= self.rule_proftax
        developer_rules |= self.rule_child
        developer_rules |= self.rule_net
        return developer_rules

    def _get_sales_rules(self):
        sales_rules = self.SalaryRule
        sales_rules |= self.rule_basic
        sales_rules |= self.rule_commission
        sales_rules |= self.rule_gross
        sales_rules |= self.rule_net
        sales_rules |= self.rule_child
        return sales_rules

    def test_use_different_structure(self):
        developer_rules = self._get_developer_rules()

        self.apply_contract_cron()
        payslip = self.Payslip.create({"employee_id": self.sally.id})
        payslip.onchange_employee()
        payslip.struct_id = self.developer_pay_structure
        self.assertNotEqual(
            payslip.struct_id,
            self.sally.contract_id.struct_id,
            "The salary structure on the payslip is different from the contract",
        )
        rules = payslip._get_salary_rules()
        self.assertEqual(
            rules,
            developer_rules,
            "The rules are the ones in the manually changed salary structure",
        )

    def test_get_salary_rules_singleton(self):
        developer_rules = self._get_developer_rules()

        self.apply_contract_cron()
        payslip = self.Payslip.create({"employee_id": self.richard_emp.id})
        payslip.onchange_employee()
        rules = payslip._get_salary_rules()
        self.assertEqual(
            payslip.struct_id,
            self.developer_pay_structure,
            "The salary structure on the payslip is same as on contract",
        )
        self.assertEqual(
            rules,
            developer_rules,
            "The rules returned correspond to the rules in the salary structure",
        )

    def test_get_salary_rules_multi(self):
        sales_allowance = self.SalaryRule.create(
            {
                "name": "Sales Allowance",
                "code": "SAA",
                "sequence": 5,
                "category_id": self.categ_alw.id,
                "condition_select": "none",
                "amount_select": "fix",
                "amount_fix": 100.0,
            }
        )
        self.sales_pay_structure.rule_ids = [(4, sales_allowance.id)]
        sales_rules = self.SalaryRule
        sales_rules |= sales_allowance
        developer_rules = self._get_developer_rules()

        self.apply_contract_cron()
        payslips = self.Payslip.create(
            [
                {"employee_id": self.richard_emp.id},
                {"employee_id": self.sally.id},
            ]
        )
        payslips.onchange_employee()
        rules = payslips._get_salary_rules()
        self.assertEqual(
            rules,
            developer_rules | sales_rules,
            "The rules returned correspond to the rules in the salary structures",
        )
        self.assertEqual(
            len(rules),
            len(developer_rules | sales_rules),
            "There are no duplicates in returned rules",
        )

    def test_get_payslip_line_singleton(self):
        self.apply_contract_cron()
        payslip = self.Payslip.create({"employee_id": self.sally.id})
        payslip.onchange_employee()

        line_key = f"BASIC-{self.sally.contract_id.id}"
        lines_dict = payslip.get_lines_dict()
        self.assertIn(
            line_key,
            lines_dict.keys(),
            "A line exists for the BASIC rule in the salary structure",
        )

    def test_get_payslip_line_multi(self):
        self.apply_contract_cron()
        payslips = self.Payslip.create(
            [
                {"employee_id": self.richard_emp.id},
                {"employee_id": self.sally.id},
            ]
        )
        payslips.onchange_employee()

        sally_key = f"BASIC-{self.sally.contract_id.id}"
        richard_key = f"BASIC-{self.richard_emp.contract_id.id}"
        lines_dict = payslips.get_lines_dict()
        self.assertIn(
            sally_key, lines_dict.keys(), "A line was created for Sally's contract"
        )
        self.assertIn(
            richard_key, lines_dict.keys(), "A line was created for Richard's contract"
        )

    def test_onchange_struct_id_singleton(self):
        new_struct = self.PayrollStructure.create(
            {
                "name": "Simple Structure",
                "code": "ST",
                "company_id": self.ref("base.main_company"),
                "rule_ids": [
                    (4, self.rule_commission.id),
                    (4, self.rule_basic.id),
                ],
            }
        )
        self.apply_contract_cron()
        payslip = self.Payslip.create({"employee_id": self.sally.id})
        payslip.onchange_employee()
        self.assertEqual(
            payslip._get_salary_rules(),
            self._get_sales_rules(),
            "Initial rules is same as structure on contract",
        )

        payslip.struct_id = new_struct
        payslip.onchange_struct_id()
        self.assertEqual(
            payslip._get_salary_rules(),
            self.rule_commission | self.rule_basic,
            "Salary rules have changed to new structure",
        )

        payslip.struct_id = False
        payslip.onchange_struct_id()
        self.assertFalse(
            payslip.input_line_ids,
            "No salary inputs because there isn't a salary structure",
        )

    def test_onchange_struct_id_multi(self):
        new_struct = self.PayrollStructure.create(
            {
                "name": "Simple Structure",
                "code": "ST",
                "company_id": self.ref("base.main_company"),
                "rule_ids": [
                    (4, self.rule_commission.id),
                    (4, self.rule_basic.id),
                ],
            }
        )
        self.apply_contract_cron()
        payslips = self.Payslip.create(
            [
                {"employee_id": self.richard_emp.id},
                {"employee_id": self.sally.id},
            ]
        )
        payslips.onchange_struct_id()
        self.assertEqual(
            payslips[0]._get_salary_rules(),
            self._get_developer_rules(),
            "Initial rules is same as structure on contract for 1st slip",
        )
        self.assertEqual(
            payslips[1]._get_salary_rules(),
            self._get_sales_rules(),
            "Initial rules is same as structure on contract for 2nd slip",
        )

        payslips.struct_id = new_struct
        payslips.onchange_struct_id()
        self.assertEqual(
            payslips[0]._get_salary_rules(),
            self.rule_commission | self.rule_basic,
            "For 1st slip salary rules have changed to new structure",
        )
        self.assertEqual(
            payslips[1]._get_salary_rules(),
            self.rule_commission | self.rule_basic,
            "For 2nd slip salary rules have changed to new structure",
        )

    def test_onchange_dates_singleton(self):
        self.apply_contract_cron()
        payslip = self.Payslip.create({"employee_id": self.sally.id})
        self.assertFalse(payslip.worked_days_line_ids)
        payslip.worked_days_line_ids = [
            (0, 0, {"name": "A", "code": "A", "contract_id": self.sally.contract_id.id})
        ]
        payslip.write({"date_from": False, "date_to": False})
        payslip.onchange_dates()
        self.assertIn(
            "A",
            payslip.worked_days_line_ids.mapped("code"),
            "One of date_from/date_end being false leaves worked_days_lines unchanged",
        )

    def test_onchange_dates_multi(self):
        self.apply_contract_cron()
        payslips = self.Payslip.create(
            [
                {"employee_id": self.richard_emp.id},
                {"employee_id": self.sally.id},
            ]
        )
        payslips[0].worked_days_line_ids = [
            (
                0,
                0,
                {
                    "name": "A",
                    "code": "A",
                    "contract_id": self.richard_emp.contract_id.id,
                },
            )
        ]
        payslips[1].worked_days_line_ids = [
            (0, 0, {"name": "B", "code": "B", "contract_id": self.sally.contract_id.id})
        ]
        payslips.write({"date_from": False, "date_to": False})
        payslips.onchange_dates()
        self.assertIn(
            "A",
            payslips[0].worked_days_line_ids.mapped("code"),
            "1st - date_from/date_end being false leaves worked_days_lines unchanged",
        )
        self.assertIn(
            "B",
            payslips[1].worked_days_line_ids.mapped("code"),
            "2nd - date_from/date_end being false leaves worked_days_lines unchanged",
        )

    def test_onchange_employee(self):
        self.apply_contract_cron()
        payslip = self.Payslip.create({"employee_id": self.sally.id})
        payslip.name = "Random name Foo"
        payslip.write({"date_from": False, "date_to": False})
        payslip.onchange_employee()
        self.assertEqual(
            payslip.name,
            "Random name Foo",
            "Payslip name not changed because date_from/date_to was False",
        )

        john = self.env["hr.employee"].create(
            {
                "name": "John",
            }
        )
        payslip = self.Payslip.create({"employee_id": john.id})
        self.assertFalse(payslip.worked_days_line_ids)
        payslip.name = "Random name Bar"
        payslip.onchange_dates()
        self.assertEqual(
            payslip.name,
            "Random name Bar",
            "Payslip name not changed because there is no contract",
        )
