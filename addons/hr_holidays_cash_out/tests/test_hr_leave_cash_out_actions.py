from odoo.exceptions import UserError

from odoo.addons.hr_holidays_cash_out.tests.common import (
    TestHrLeaveCashOutCommon,
)


class TestActionsBaseUser(TestHrLeaveCashOutCommon):
    """Test the hr.leave.cash.out actions for base.group_user"""
    # TODO: Add test to assert that a user cannot a cash out request that is created in the past.
    def test_action_cancel(self):
        """A normal user can cancel their own cash out request only and only if they are in validate state."""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_hruser.id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        hruser_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hruser_id},
        )
        with self.assertRaises(UserError, msg="You cannot cancel a cash out request that is in the 'confirm' state."):
            employee_cash_out.action_cancel()
        employee_cash_out.with_user(self.user_hruser_id).action_approve()
        employee_cash_out.with_user(self.user_employee_id).action_cancel()
        with self.assertRaises(UserError, msg="You cannot cancel a cash out request that is in the 'cancel' state."):
            employee_cash_out.with_user(self.user_employee_id).action_cancel()
        hruser_cash_out.with_user(self.user_hrmanager_id).action_approve()
        with self.assertRaises(UserError, msg="You cannot cancel a cash out request that is not yours."):
            hruser_cash_out.with_user(self.user_employee_id).action_cancel()

    def test_action_approve(self):
        """A normal user cannot approve a cash out request."""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_hruser.id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        hruser_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hruser_id},
        )
        with self.assertRaises(UserError, msg="You cannot approve a cash out request that is not yours."):
            hruser_cash_out.with_user(self.user_employee_id).action_approve()
        with self.assertRaises(UserError, msg="You cannot approve your cash out request."):
            employee_cash_out.with_user(self.user_employee_id).action_approve()

    def test_action_refuse(self):
        """A normal user cannot refuse a cash out request."""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_hruser.id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        hruser_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hruser_id},
        )
        with self.assertRaises(UserError, msg="You cannot refuse a cash out request that is not yours."):
            hruser_cash_out.with_user(self.user_employee_id).action_refuse()
        with self.assertRaises(UserError, msg="You cannot refuse your cash out request."):
            employee_cash_out.with_user(self.user_employee_id).action_refuse()

# class TestActionsHolidaysResponsible(TestHrLeaveCashOutCommon):
