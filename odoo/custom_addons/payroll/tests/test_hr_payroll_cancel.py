# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from dateutil import relativedelta

from odoo.exceptions import ValidationError
from odoo.tests import common


class TestHrPayrollCancel(common.TransactionCase):
    def setUp(self):
        super().setUp()
        # Set system parameter
        self.env["ir.config_parameter"].sudo().set_param(
            "payroll.allow_cancel_payslips", True
        )
        self.payslip_action_id = self.ref("payroll.hr_payslip_menu")
        self.res_partner_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "001-9876543-21",
                "partner_id": self.ref("base.res_partner_12"),
                "acc_type": "bank",
                "bank_id": self.ref("base.res_bank_1"),
            }
        )
        self.hr_employee_anita = self.env.ref("hr.employee_mit")
        self.hr_contract_anita = self.env.ref("hr_contract.hr_contract_mit")
        self.hr_payslip = self.env["hr.payslip"].create(
            {
                "employee_id": self.hr_employee_anita.id,
            }
        )

    def test_refund_sheet(self):
        hr_payslip = self._create_payslip()
        hr_payslip.action_payslip_done()
        hr_payslip.refund_sheet()
        with self.assertRaises(ValidationError):
            hr_payslip.action_payslip_cancel()
        self.assertEqual(hr_payslip.refunded_id.state, "done")
        hr_payslip.refunded_id.action_payslip_cancel()
        self.assertEqual(hr_payslip.refunded_id.state, "cancel")
        self.assertEqual(hr_payslip.state, "done")
        hr_payslip.action_payslip_cancel()
        self.assertEqual(hr_payslip.state, "cancel")

    def _create_payslip(self):
        date_from = datetime.now()
        date_to = datetime.now() + relativedelta.relativedelta(
            months=+2, day=1, days=-1
        )
        res = self.hr_payslip.get_payslip_vals(
            date_from, date_to, self.hr_employee_anita.id
        )
        vals = {
            "struct_id": res["value"]["struct_id"],
            "contract_id": res["value"]["contract_id"],
            "name": res["value"]["name"],
        }
        vals["worked_days_line_ids"] = [
            (0, 0, i) for i in res["value"]["worked_days_line_ids"]
        ]
        vals["input_line_ids"] = [(0, 0, i) for i in res["value"]["input_line_ids"]]
        vals.update({"contract_id": self.hr_contract_anita.id})
        self.hr_payslip.write(vals)
        payslip_input = self.env["hr.payslip.input"].search(
            [("payslip_id", "=", self.hr_payslip.id)]
        )
        payslip_input.write({"amount": 5.0})
        self.hr_payslip.with_context(
            {},
            lang="en_US",
            tz=False,
            active_model="hr.payslip",
            department_id=False,
            active_ids=[self.payslip_action_id],
            section_id=False,
            active_id=self.payslip_action_id,
        ).compute_sheet()
        return self.hr_payslip

    def test_action_payslip_cancel(self):
        hr_payslip = self._create_payslip()
        hr_payslip.action_payslip_done()
        hr_payslip.refund_sheet()
        hr_payslip.refunded_id.action_payslip_cancel()
        hr_payslip.action_payslip_cancel()
