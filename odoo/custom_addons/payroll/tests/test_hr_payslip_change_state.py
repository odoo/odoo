# Copyright 2019 - Eficent http://www.eficent.com/
# Copyright 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError

from odoo.addons.payroll.tests.test_hr_payroll_cancel import TestHrPayrollCancel


class TestHrPayslipChangeState(TestHrPayrollCancel):
    def setUp(self):
        super().setUp()
        self.tested_model = self.env["hr.payslip.change.state"]

    def test_change_state(self):
        hr_payslip = self._create_payslip()
        tested_model = self.tested_model
        action = tested_model.with_context({}, active_ids=[hr_payslip.id]).create(
            {"state": "verify"}
        )
        # By default, a payslip is on draft state
        action.change_state_confirm()
        # trying to set it to wrong states
        with self.assertRaises(UserError):
            action.write({"state": "draft"})
            action.change_state_confirm()
        # Now the payslip should be computed but in verify state
        self.assertEqual(hr_payslip.state, "verify")
        self.assertNotEqual(hr_payslip.number, None)
        action.write({"state": "done"})
        action.change_state_confirm()
        # Now the payslip should be confirmed
        self.assertEqual(hr_payslip.state, "done")
        # trying to set it to wrong states
        with self.assertRaises(UserError):
            action.write({"state": "draft"})
            action.change_state_confirm()
        with self.assertRaises(UserError):
            action.write({"state": "verify"})
            action.change_state_confirm()
        with self.assertRaises(UserError):
            action.write({"state": "done"})
            action.change_state_confirm()
        action.write({"state": "cancel"})
        action.change_state_confirm()
        # Now the payslip should be canceled
        self.assertEqual(hr_payslip.state, "cancel")
        # trying to set it to wrong states
        with self.assertRaises(UserError):
            action.write({"state": "done"})
            action.change_state_confirm()
        with self.assertRaises(UserError):
            action.write({"state": "verify"})
            action.change_state_confirm()
        with self.assertRaises(UserError):
            action.write({"state": "cancel"})
            action.change_state_confirm()
        action.write({"state": "draft"})
        action.change_state_confirm()
        # again, it should be draft. Also checking if wrong changes happened
        self.assertEqual(hr_payslip.state, "draft")
