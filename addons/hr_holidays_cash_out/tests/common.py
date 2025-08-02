import time

from odoo import tests

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon



@tests.tagged("access_rights", "post_install", "-at_install")
class TestHrLeaveCashOutCommon(TestHrHolidaysCommon):
    """Test the access rights for hr_leave_cash_out"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Leave Type",
                "leave_validation_type": "hr",
                "requires_allocation": True,
                "allow_cash_out_request": True,
                "allow_employee_request": True,
            },
        )
        cls.rd_dept.manager_id = False
        cls.hr_dept.manager_id = False
        cls.employee_emp.parent_id = False
        cls.cash_out_states = [
            state[0]
            for state in cls.env["hr.leave.cash.out"]._fields["state"].selection
        ]

    def request_allocation(self, values={}):
        values = {
            "name": "Allocation",
            "number_of_days": 20,
            "date_from": time.strftime("%Y-01-01"),
            "date_to": time.strftime("%Y-12-31"),
            "holiday_status_id": self.leave_type.id,
            **values,
        }
        allocation = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hrmanager_id)
            .create(values)
        )
        return allocation.with_user(self.user_hrmanager_id).action_approve()

    def request_cash_out(self, user, values={}):
        values = {
            "state": "confirm",
            "leave_type_id": self.leave_type.id,
            "quantity": 1,
            **values,
        }
        return self.env["hr.leave.cash.out"].with_context(employee_id=values['employee_id']).with_user(user).create(values)
