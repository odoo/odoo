import time

from odoo import tests
from odoo.exceptions import AccessError
from odoo.tools import mute_logger

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tests.tagged("access_rights", "post_install", "-at_install")
class TestHrLeaveCashOutAccessRightsCommon(TestHrHolidaysCommon):
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


@tests.tagged("access_rights")
class TestAccessRightsBaseUser(TestHrLeaveCashOutAccessRightsCommon):
    """Test the access rights for base.group_user"""

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_base_user_read(self):
        """A normal user can read his cash out requests only"""
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
        try:
            employee_cash_out.with_user(self.user_employee.id).read(
                ["state", "quantity", "employee_id"],
            )
            read_succeeded = True
        except AccessError:
            read_succeeded = False
        self.assertTrue(read_succeeded, "User should be able to read his cash request")
        with self.assertRaises(AccessError):
            hruser_cash_out.with_user(self.user_employee.id).read(
                ["state", "quantity", "employee_id"],
            )

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_base_user_write(self):
        """A normal user can write his cash out requests only and only if they are not in validate/validate1 state"""
        self.request_allocation(
            {
                "employee_id": self.employee_hruser.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        try:
            employee_cash_out.with_user(self.user_employee_id).write(
                {"quantity": 2},
            )
            edit_succeeded = True
        except AccessError:
            edit_succeeded = False
        self.assertTrue(
            edit_succeeded,
            "User should be able to edit his cash request in confirm state",
        )
        employee_cash_out = self.request_cash_out(
            self.user_hrmanager_id,
            {"employee_id": self.employee_emp_id, "state": "validate"},
        )
        with self.assertRaises(AccessError):
            employee_cash_out.with_user(self.user_employee_id).write(
                {"quantity": 2},
            )
        hruser_cash_out = self.request_cash_out(
            self.user_hrmanager_id,
            {"employee_id": self.employee_hruser_id, "state": "validate"},
        )
        with self.assertRaises(AccessError):
            hruser_cash_out.with_user(self.user_employee_id).write(
                {"quantity": 2},
            )

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_base_user_create(self):
        """A normal user can create his cash out requests only and only if they are in confirm state"""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        cash_out_vals = {
            "employee_id": self.employee_emp.id,
        }
        for state in self.cash_out_states:
            if state == "confirm":
                self.request_cash_out(
                    self.user_employee.id,
                    {**cash_out_vals, "state": state},
                )
            else:
                with self.assertRaises(AccessError):
                    self.request_cash_out(
                        self.user_employee.id,
                        {**cash_out_vals, "state": state},
                    )

        self.request_allocation(
            {
                "employee_id": self.employee_hruser.id,
            },
        )
        with self.assertRaises(AccessError):
            self.request_cash_out(
                self.user_employee_id,
                {**cash_out_vals, "employee_id": self.employee_hruser_id},
            )

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_base_user_delete(self):
        """A normal user can delete his cash out requests only and only if they are in confirm/validate1 state"""
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
        cash_out_vals = {
            "employee_id": self.employee_emp.id,
        }
        for state in self.cash_out_states:
            employee_cash_out = self.request_cash_out(
                self.user_hrmanager_id,
                {**cash_out_vals, "state": state},
            )
            if state in ["confirm", "validate1"]:
                try:
                    employee_cash_out.with_user(self.user_employee.id).unlink()
                    delete_succeeded = True
                except AccessError:
                    delete_succeeded = False
                self.assertTrue(
                    delete_succeeded,
                    "User should be able to delete his cash request in confirm state",
                )
            else:
                with self.assertRaises(AccessError):
                    employee_cash_out.with_user(self.user_employee.id).unlink()
        hruser_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hruser_id},
        )
        with self.assertRaises(AccessError):
            hruser_cash_out.with_user(self.user_employee_id).unlink()


@tests.tagged("access_rights")
class TestAccessRightsHolidaysResponsible(TestHrLeaveCashOutAccessRightsCommon):
    """Test the access rights for hr_holidays.group_hr_holidays_responsible"""

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_holidays_responsible_read(self):
        """A time off responsible can read cash out requests for all employees he manage"""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_hrmanager_id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        manager_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hrmanager_id},
        )
        try:
            employee_cash_out.with_user(self.user_responsible_id).read(
                ["state", "quantity", "employee_id"],
            )
            read_succeeded = True
        except AccessError:
            read_succeeded = False
        self.assertTrue(read_succeeded, "Holidays responsible should be able to read his cash requests of employees he manages")
        with self.assertRaises(AccessError):
            manager_cash_out.with_user(self.user_responsible_id).read(
                ["state", "quantity", "employee_id"],
            )

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_holidays_responsible_write(self):
        """A time off responsible can write cash out requests for all employees he manage"""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_hrmanager_id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        manager_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hrmanager_id},
        )
        try:
            employee_cash_out.with_user(self.user_responsible_id).write(
                {"quantity": 2},
            )
            read_succeeded = True
        except AccessError:
            read_succeeded = False
        self.assertTrue(read_succeeded, "Holidays responsible should be able to write his cash requests of employees he manages")
        with self.assertRaises(AccessError):
            manager_cash_out.with_user(self.user_responsible_id).write(
                {"quantity": 2},
            )


@tests.tagged("access_rights")
class TestAccessRightsHrHolidaysUser(TestHrLeaveCashOutAccessRightsCommon):
    """Test the access rights for hr_holidays.group_hr_holidays_user"""

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_holidays_user_read(self):
        """A time off officer can read cash out requests for all employees"""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_responsible.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_hrmanager_id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        responsible_cash_out = self.request_cash_out(
            self.user_hrmanager_id,
            {"employee_id": self.employee_responsible.id},
        )
        manager_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hrmanager_id},
        )
        cash_out_reuests = [
            employee_cash_out,
            responsible_cash_out,
            manager_cash_out,
        ]
        for cash_out in cash_out_reuests:
            try:
                cash_out.with_user(self.user_hruser_id).read(
                    ["state", "quantity", "employee_id"],
                )
                read_succeeded = True
            except AccessError:
                read_succeeded = False
            self.assertTrue(read_succeeded, "Holidays user should be able to read cash requests of all employees")

    @mute_logger("odoo.models.unlink", "odoo.addons.mail.models.mail_mail")
    def test_holidays_user_write(self):
        """A time off officer can write cash out request for all employees
        but he can neither approve nor validate his own requests"""
        self.request_allocation(
            {
                "employee_id": self.employee_emp.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_responsible.id,
            },
        )
        self.request_allocation(
            {
                "employee_id": self.employee_hruser_id,
            },
        )
        employee_cash_out = self.request_cash_out(
            self.user_employee_id,
            {"employee_id": self.employee_emp_id},
        )
        responsible_cash_out = self.request_cash_out(
            self.user_hrmanager_id,
            {"employee_id": self.employee_responsible.id},
        )
        hruser_cash_out = self.request_cash_out(
            self.user_hruser_id,
            {"employee_id": self.employee_hruser_id},
        )
        try:
            employee_cash_out.with_user(self.user_hruser_id).write(
                {"quantity": 2},
            )
            responsible_cash_out.with_user(self.user_hruser_id).write(
                {"quantity": 2},
            )
            write_succeeded = True
        except AccessError:
            write_succeeded = False
        self.assertTrue(write_succeeded, "Holidays user should be able to write cash requests of all employees")
        with self.assertRaises(AccessError):
            hruser_cash_out.with_user(self.user_hruser_id).action_approve()
