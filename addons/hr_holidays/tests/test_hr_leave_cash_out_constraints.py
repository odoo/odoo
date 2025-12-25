from psycopg2.errors import CheckViolation

from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

from odoo.addons.hr_holidays.tests.common import (
    TestHrLeaveCashOutCommon,
)


class TestHrLeaveCashOutConstraints(TestHrLeaveCashOutCommon):
    """Test the constraints for hr.leave.cash.out."""

    def test_allow_cash_out_request(self):
        """Test that cash out requests are allowed."""
        emp_allocation = self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        try:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "leave_allocation_id": emp_allocation.id},
            )
            create_succeeded = True
        except ValidationError:
            create_succeeded = False
        self.assertTrue(
            create_succeeded,
            "Cash out request should be allowed when allow_cash_out_request is True.",
        )
        self.leave_type.allow_cash_out_request = False

        with self.assertRaises(ValidationError) as e:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "leave_allocation_id": emp_allocation.id},
            )
        self.assertIn("The selected leave type does not allow cash out requests.", str(e.exception))

    def test_allow_employee_request(self):
        """Test that cash out requests are allowed for employees."""
        emp_allocation = self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        try:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "leave_allocation_id": emp_allocation.id},
            )
            create_succeeded = True
        except ValidationError:
            create_succeeded = False
        self.assertTrue(
            create_succeeded,
            "Cash out request should be allowed when allow_employee_request is True.",
        )
        self.leave_type.allow_employee_request = False

        with self.assertRaises(ValidationError) as e:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "leave_allocation_id": emp_allocation.id},
            )
        self.assertIn("Only an officer or an administrator can create a cash out request of this time off type.", str(e.exception))

    @mute_logger('odoo.sql_db')
    def test_quantity_check(self):
        """Test that the quantity is a positive number."""
        emp_allocation = self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        with self.assertRaises(CheckViolation) as e:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "quantity": 0, "leave_allocation_id": emp_allocation.id},
            )
        self.assertIn("hr_leave_cash_out_quantity_check", str(e.exception))
        with self.assertRaises(CheckViolation) as e:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "quantity": -1, "leave_allocation_id": emp_allocation.id},
            )
        self.assertIn("hr_leave_cash_out_quantity_check", str(e.exception))
        try:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "quantity": 1, "leave_allocation_id": emp_allocation.id},
            )
            create_succeeded = True
        except CheckViolation:
            create_succeeded = False
        self.assertTrue(
            create_succeeded,
            "Cash out request should be allowed with a positive quantity.",
        )

    def test_requires_allocation(self):
        """Test that leave types for a cash out requests must require an allocation."""
        emp_allocation = self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.leave_type.requires_allocation = False
        with self.assertRaises(ValidationError) as e:
            self.request_cash_out(
                self.user_employee_id,
                {"employee_id": self.employee_emp_id, "leave_allocation_id": emp_allocation.id},
            )
        self.assertIn("The selected leave type should require allocation.", str(e.exception))
