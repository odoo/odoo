from odoo import Command
from odoo.tests import Form, tagged

from .common import TestPayrollCommon


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestContract(TestPayrollCommon):

    def test_contract_creation_with_zero_working_hours(self):
        self.env.company.resource_calendar_id.attendance_ids = [Command.clear()]
        employee = self.env['hr.employee'].create({
            "name": "Au Employee",
            "company_id": self.australian_company.id,
        })
        with Form(self.env['hr.contract']) as contract_form:
            contract_form.employee_id = employee
            contract_form.name = "Au Employee Contract"
            contract_form.wage = 100
            contract_form.wage_type = "monthly"
            contract_form.l10n_au_yearly_wage = 1200
        contract = contract_form.save()

        self.assertTrue(contract)
        self.assertEqual(contract.hourly_wage, 0.0)
