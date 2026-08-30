from datetime import date, timedelta

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.fields import Date, Datetime
from odoo.tests import Form, tagged, users
from odoo.tools import format_date

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("allocation")
class TestAllocations(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Time Off with no validation for approval",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
            }
        )
        cls.department = cls.env["hr.department"].create(
            {
                "name": "Test Department",
            }
        )
        cls.category_tag = cls.env["res.partner.tag"].create({"name": "Test category"})
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "My Employee",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
                "tag_ids": [(4, cls.category_tag.id)],
            }
        )

        cls.leave_type_paid = cls.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
            }
        )

        cls.calendar_35h = cls.env["resource.calendar"].create(
            {
                "name": "Calendar - 35H",
                "company_id": cls.company.id,
                "attendance_ids": [
                    (5, 0, 0),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Morning",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Lunch",
                            "dayofweek": "0",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Afternoon",
                            "dayofweek": "0",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Morning",
                            "dayofweek": "1",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Lunch",
                            "dayofweek": "1",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Afternoon",
                            "dayofweek": "1",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Morning",
                            "dayofweek": "2",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Lunch",
                            "dayofweek": "2",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Afternoon",
                            "dayofweek": "2",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Morning",
                            "dayofweek": "3",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Lunch",
                            "dayofweek": "3",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Afternoon",
                            "dayofweek": "3",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Morning",
                            "dayofweek": "4",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Lunch",
                            "dayofweek": "4",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Afternoon",
                            "dayofweek": "4",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                ],
            }
        )

    def test_allocation_whole_company(self):
        company_allocation = self.env[
            "hr.leave.allocation.generate.multi.wizard"
        ].create(
            {
                "name": "Bank Holiday",
                "allocation_mode": "company",
                "company_id": self.company.id,
                "holiday_status_id": self.leave_type.id,
                "duration": 2,
                "allocation_type": "regular",
            }
        )

        company_allocation.action_generate_allocations()

        num_of_allocations = self.env["hr.leave.allocation"].search_count(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_multi_employee(self):
        employee_allocation = self.env[
            "hr.leave.allocation.generate.multi.wizard"
        ].create(
            {
                "name": "Bank Holiday",
                "allocation_mode": "employee",
                "employee_ids": [(4, self.employee.id), (4, self.employee_emp.id)],
                "holiday_status_id": self.leave_type.id,
                "duration": 2,
                "allocation_type": "regular",
            }
        )

        employee_allocation.action_generate_allocations()

        num_of_allocations = self.env["hr.leave.allocation"].search_count(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_department(self):
        department_allocation = self.env[
            "hr.leave.allocation.generate.multi.wizard"
        ].create(
            {
                "name": "Bank Holiday",
                "allocation_mode": "department",
                "department_id": self.department.id,
                "holiday_status_id": self.leave_type.id,
                "duration": 2,
                "allocation_type": "regular",
            }
        )

        department_allocation.action_generate_allocations()

        num_of_allocations = self.env["hr.leave.allocation"].search_count(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertEqual(num_of_allocations, 1)

    @users("Titus")
    def test_create_group_allocation_without_hr_right(self):
        employee_1, employee_2 = (
            self.env["hr.employee"]
            .sudo()
            .create(
                [
                    {
                        "name": "Emp1",
                        "leave_manager_id": self.user_responsible_id,
                    },
                    {
                        "name": "Emp2",
                        "leave_manager_id": self.user_responsible_id,
                    },
                ]
            )
        )
        allocation_wizard = self.env[
            "hr.leave.allocation.generate.multi.wizard"
        ].create(
            {
                "holiday_status_id": self.leave_type.id,
                "date_from": date(2019, 5, 6),
                "date_to": date(2019, 5, 6),
                "employee_ids": (employee_1 + employee_2).ids,
                "duration": 2,
                "allocation_type": "regular",
            }
        )
        allocation_wizard.action_generate_allocations()

    def test_allocation_category(self):
        category_allocation = self.env[
            "hr.leave.allocation.generate.multi.wizard"
        ].create(
            {
                "name": "Bank Holiday",
                "allocation_mode": "category",
                "tag_id": self.category_tag.id,
                "holiday_status_id": self.leave_type.id,
                "duration": 2,
                "allocation_type": "regular",
            }
        )

        category_allocation.action_generate_allocations()

        num_of_allocations = self.env["hr.leave.allocation"].search_count(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_request_day(self):
        self.leave_type.write(
            {"name": "Custom Time Off Test", "allocation_validation_type": "hr"}
        )

        employee_allocation = self.env["hr.leave.allocation"].create(
            {
                "employee_id": self.employee.id,
                "holiday_status_id": self.leave_type.id,
                "allocation_type": "regular",
            }
        )

        with Form(
            employee_allocation,
            "hr_holidays.hr_leave_allocation_view_form_dashboard",
        ) as allocation:
            allocation.number_of_days_display = 10
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.name, "Custom Time Off Test (10.0 day(s))")

    def test_allocation_request_half_days(self):
        self.leave_type.write(
            {"name": "Custom Time Off Test", "allocation_validation_type": "hr"}
        )

        employee_allocation = self.env["hr.leave.allocation"].create(
            {
                "employee_id": self.employee.id,
                "holiday_status_id": self.leave_type.id,
                "allocation_type": "regular",
                "type_request_unit": "half_day",
            }
        )

        with Form(
            employee_allocation,
            "hr_holidays.hr_leave_allocation_view_form_dashboard",
        ) as allocation:
            allocation.number_of_days_display = 10
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.name, "Custom Time Off Test (10.0 day(s))")

    def test_a_day_allocation_returning_from_accrual_asks_for_one_day(self):
        """`_onchange_allocation_type` empties an allocation turned into an
        accrual one, and offers a day back when it is turned into a regular one
        with nothing in it.

        Was `change_allocation_type_day`, which the runner never collected: the
        name did not start with `test`, it wrote a `holiday_type` this model has
        not had for some time, and it moved `allocation_type` through "extra",
        which is not one of its two values.
        """
        self.leave_type.write(
            {"name": "Custom Time Off Test", "allocation_validation_type": "hr"}
        )

        with Form(
            self.env["hr.leave.allocation"],
            "hr_holidays.hr_leave_allocation_view_form_manager",
        ) as allocation:
            allocation.employee_id = self.employee
            allocation.holiday_status_id = self.leave_type
            allocation.allocation_type = "accrual"
            self.assertEqual(allocation.number_of_days, 0.0)
            allocation.allocation_type = "regular"
            self.assertEqual(allocation.number_of_days, 1.0)
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.number_of_days, 1.0)

    def test_allocation_type_hours_with_resource_calendar(self):
        self.leave_type.request_unit = "hour"
        self.employee.resource_calendar_id = self.calendar_35h

        hour_type_allocation = self.env[
            "hr.leave.allocation.generate.multi.wizard"
        ].create(
            {
                "name": "Hours Allocation",
                "allocation_mode": "employee",
                "employee_ids": [(4, self.employee.id), (4, self.employee_emp.id)],
                "holiday_status_id": self.leave_type.id,
                "duration": 10,
                "allocation_type": "regular",
            }
        )

        self.assertEqual(self.employee.resource_calendar_id.hours_per_day, 7.0)
        self.assertEqual(self.employee_emp.resource_calendar_id.hours_per_day, 8.0)

        hour_type_allocation.action_generate_allocations()

        employee_allocation = self.env["hr.leave.allocation"].search(
            [
                ("employee_id", "=", self.employee.id),
            ]
        )
        employee_emp_allocation = self.env["hr.leave.allocation"].search(
            [
                ("employee_id", "=", self.employee_emp.id),
            ]
        )

        self.assertEqual(employee_allocation.number_of_hours_display, 10)
        self.assertEqual(employee_emp_allocation.number_of_hours_display, 10)

    def test_an_hour_allocation_returning_from_accrual_asks_for_one_day(self):
        """The same, for a type requested in hours.

        Was `change_allocation_type_hours`, dead for the same three reasons, and
        additionally setting `type_request_unit` in `create` -- a compute with
        no writable side, so the unit has to come from the leave type.
        """
        self.leave_type.write(
            {
                "name": "Custom Time Off Test",
                "allocation_validation_type": "hr",
                "request_unit": "hour",
            }
        )

        with Form(
            self.env["hr.leave.allocation"],
            "hr_holidays.hr_leave_allocation_view_form_manager",
        ) as allocation:
            allocation.employee_id = self.employee
            allocation.holiday_status_id = self.leave_type
            self.assertEqual(allocation.type_request_unit, "hour")
            allocation.allocation_type = "accrual"
            self.assertEqual(allocation.number_of_days, 0.0)
            allocation.allocation_type = "regular"
            self.assertEqual(allocation.number_of_days, 1.0)
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.number_of_days, 1.0)

    def test_allowed_change_allocation(self):
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Initial Allocation",
                "holiday_status_id": self.leave_type_paid.id,
                "number_of_days": 20,
                "employee_id": self.employee.id,
                "date_from": date(2024, 1, 1),
            }
        )
        allocation.action_approve()

        leave_request = self.env["hr.leave"].create(
            {
                "name": "Leave Request",
                "holiday_status_id": self.leave_type_paid.id,
                "request_date_from": date(2024, 1, 5),
                "request_date_to": date(2024, 1, 10),
                "employee_id": self.employee.id,
            }
        )
        leave_request.action_approve()
        allocation.write({"number_of_days_display": 14, "number_of_days": 14})
        self.assertEqual(allocation.number_of_days_display, 14)

        with self.assertRaises(ValidationError):
            allocation.write({"number_of_days_display": 2, "number_of_days": 2})

    def test_disallowed_change_allocation_with_overlapping_allocations(self):
        allocation_one = self.env["hr.leave.allocation"].create(
            {
                "name": "First Allocation",
                "holiday_status_id": self.leave_type_paid.id,
                "number_of_days": 5,
                "employee_id": self.employee.id,
                "date_from": date(2024, 1, 1),
                "date_to": date(2024, 1, 30),
            }
        )
        allocation_one.action_approve()

        allocation_two = self.env["hr.leave.allocation"].create(
            {
                "name": "Second Half Allocation",
                "holiday_status_id": self.leave_type_paid.id,
                "number_of_days": 5,
                "employee_id": self.employee.id,
                "date_from": date(2024, 1, 20),
                "date_to": date(2024, 2, 20),
            }
        )
        allocation_two.action_approve()

        leave_request = self.env["hr.leave"].create(
            {
                "name": "Leave Request Spanning Allocations",
                "holiday_status_id": self.leave_type_paid.id,
                "request_date_from": date(2024, 1, 25),
                "request_date_to": date(2024, 2, 5),
                "employee_id": self.employee.id,
            }
        )
        leave_request.action_approve()

        with self.assertRaises(ValidationError):
            allocation_one.write({"number_of_days_display": 2, "number_of_days": 2})

        allocation_one.write({"number_of_days_display": 3, "number_of_days": 3})

    @users("admin")
    @freeze_time("2024-03-25")
    def test_allocation_dropdown_after_period(self):
        leave_type = self.env.ref("hr_holidays.leave_type_compensatory_days")
        allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "name": "Alloc",
                    "employee_id": self.employee.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 3,
                    "allocation_type": "regular",
                    "date_from": date(2024, 1, 1),
                    "date_to": date(2024, 4, 30),
                }
            )
        )
        allocation.action_approve()

        second_allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "name": "Alloc2",
                    "employee_id": self.employee.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 9,
                    "allocation_type": "regular",
                    "date_from": date(2024, 5, 1),
                    "date_to": date(2024, 12, 31),
                }
            )
        )
        second_allocation.action_approve()

        self.env["hr.leave.type"].invalidate_model(
            ["max_leaves", "leaves_taken", "virtual_remaining_leaves"]
        )
        result = (
            self.env["hr.leave.type"]
            .with_context(
                employee_id=self.employee.id,
                leave_date_from="2024-08-18 06:00:00",
                default_date_from="2024-08-18 06:00:00",
                default_date_to="2024-08-18 15:00:00",
            )
            .name_search(domain=[["id", "=", leave_type.id]])
        )
        self.assertEqual(result[0][1], "Compensatory Days (9 remaining out of 9 days)")

    def test_allocation_hourly_leave_type(self):
        employee = self.env["hr.employee"].create(
            {
                "name": "My Employee",
                "company_id": self.company.id,
                "resource_calendar_id": self.calendar_35h.id,
            }
        )

        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Hourly Leave Type",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "request_unit": "hour",
            }
        )

        with Form(
            self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
        ) as allocation_form:
            allocation_form.allocation_type = "regular"
            allocation_form.employee_id = employee
            allocation_form.holiday_status_id = leave_type
            allocation_form.number_of_hours_display = 10
            allocation = allocation_form.save()

        self.assertEqual(allocation.number_of_hours_display, 10.0)

    def test_automatic_allocation_type(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Hourly Leave Type",
                "requires_allocation": "yes",
                "allocation_validation_type": "no_validation",
                "request_unit": "hour",
            }
        )

        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                }
            )
        )

        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Alloc with accrual plan",
                "employee_id": self.employee.id,
                "holiday_status_id": leave_type.id,
                "accrual_plan_id": accrual_plan.id,
            }
        )

        self.assertEqual(allocation.allocation_type, "accrual")

        allocation.update(
            {
                "accrual_plan_id": False,
            }
        )

        self.assertEqual(allocation.allocation_type, "regular")

    def test_create_allocation_from_company_with_no_employee_for_current_user(self):
        self.user_hrmanager.employee_id = False
        allocation_form = Form(
            self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
        )
        self.assertFalse(allocation_form.employee_id)
        allocation_form.employee_id = self.employee
        allocation_form.holiday_status_id = self.leave_type
        allocation = allocation_form.save()
        self.assertTrue(allocation)

    def test_hr_leave_allocation_balance(self):
        leave_type = self.env.ref("hr_holidays.leave_type_compensatory_days")

        invalid_allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "name": "Alloc",
                    "employee_id": self.employee.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 5,
                    "allocation_type": "regular",
                    "date_from": date(2024, 1, 1),
                    "date_to": date(2024, 4, 30),
                }
            )
        )
        invalid_allocation.action_approve()

        first_valid_allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "name": "Alloc",
                    "employee_id": self.employee.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 10,
                    "allocation_type": "regular",
                    "date_from": date(2024, 1, 1),
                    "date_to": False,
                }
            )
        )
        first_valid_allocation.action_approve()

        second_valid_allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "name": "Alloc",
                    "employee_id": self.employee.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 12,
                    "allocation_type": "regular",
                    "date_from": date(2025, 1, 1),
                    "date_to": Date.context_today(self.env.user),
                }
            )
        )
        second_valid_allocation.action_approve()

        leave = self.env["hr.leave"].create(
            {
                "employee_id": self.employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": date(2025, 1, 1),
                "request_date_to": date(2025, 1, 10),
            }
        )
        leave._action_validate()

        self.assertEqual(leave.max_leaves, 22)
        self.assertEqual(leave.virtual_remaining_leaves, 14)

    def test_allocation_request_with_date_from(self):
        allocation = self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
        allocation_view = "hr_holidays.hr_leave_allocation_view_form"
        with self.assertRaises(AssertionError):
            with Form(allocation, allocation_view) as allocation_form:
                allocation_form.holiday_status_id = self.leave_type
                allocation_form.date_from = False

        with Form(allocation, allocation_view) as allocation_form:
            date_from = Date.today()
            allocation_form.holiday_status_id = self.leave_type
            allocation_form.date_from = date_from

            self.assertEqual(allocation_form.date_from, date_from)
            self.assertEqual(
                allocation_form.name_validity,
                "%(allocation_name)s (from %(date_from)s to No Limit)"
                % {
                    "allocation_name": allocation_form.name,
                    "date_from": format_date(
                        allocation.env,
                        Date.context_today(
                            allocation, Datetime.to_datetime(allocation_form.date_from)
                        ),
                    ),
                },
                "The name_validity field was not set correctly.",
            )

    def test_leave_allocation_by_removing_employee(self):
        self.leave_type.request_unit = "hour"
        with self.assertRaises(AssertionError):
            with Form(self.env["hr.leave.allocation"]) as allocation_form:
                allocation_form.allocation_type = "regular"
                allocation_form.holiday_status_id = self.leave_type
                allocation_form.number_of_hours_display = 10
                allocation_form.employee_id = self.env["hr.employee"]
            allocation_form.save()

    def test_employee_holidays_archived_display(self):
        admin_user = self.env.ref("base.user_admin")

        employee = self.env["hr.employee"].create(
            {
                "name": "test_employee",
            }
        )

        leave_type = self.env["hr.leave.type"].with_user(admin_user)

        holidays_type_1 = leave_type.create(
            {
                "name": "archived_holidays",
                "allocation_validation_type": "no_validation",
            }
        )

        self.env["hr.leave.allocation"].create(
            {
                "name": "archived_holidays_allocation",
                "employee_id": employee.id,
                "holiday_status_id": holidays_type_1.id,
                "number_of_days": 10,
                "state": "confirm",
                "date_from": "2022-01-01",
            }
        )

        self.assertEqual(employee.allocation_display, "10")

        holidays_type_1.active = False
        employee._compute_allocation_displays()

        self.assertEqual(employee.allocation_display, "0")

    def test_refuse_validated_allocation_with_leaves(self):
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        leave_employee = self.env["hr.employee"].create(
            {
                "name": "Test Employee",
                "user_id": self.env.uid,
            }
        )

        def _create_allocation(days):
            return self.env["hr.leave.allocation"].create(
                {
                    "name": f"{days} days Allocation",
                    "holiday_status_id": self.leave_type_paid.id,
                    "number_of_days": days,
                    "employee_id": leave_employee.id,
                    "date_from": start_of_week,
                }
            )

        allocation_5_days = _create_allocation(days=5)
        allocation_5_days.action_approve()
        self.assertEqual(allocation_5_days.state, "validate")

        leave_request = self.env["hr.leave"].create(
            {
                "name": "Leave Request",
                "holiday_status_id": self.leave_type_paid.id,
                "request_date_from": start_of_week,
                "request_date_to": start_of_week + timedelta(days=3),
                "employee_id": leave_employee.id,
            }
        )
        leave_request.action_approve()

        allocation_3_days = _create_allocation(days=3)
        allocation_3_days.date_to = start_of_week + timedelta(days=5)
        allocation_3_days.action_approve()
        self.assertEqual(allocation_3_days.state, "validate")

        with self.assertRaises(ValidationError):
            allocation_5_days.action_refuse()
        self.assertEqual(allocation_5_days.state, "validate")

        allocation_3_days.action_refuse()
        self.assertEqual(allocation_3_days.state, "refuse")
        allocation_3_days.state = "confirm"
        allocation_3_days.action_approve()
        self.assertEqual(allocation_3_days.state, "validate")

        leave_request.state = "confirm"
        leave_request.request_date_to = start_of_week + timedelta(days=1)
        leave_request.action_approve()

        allocation_5_days.action_refuse()
        self.assertEqual(allocation_5_days.state, "refuse")

        with self.assertRaises(ValidationError):
            allocation_3_days.action_refuse()
        self.assertEqual(allocation_3_days.state, "validate")

        allocation_5_days.state = "confirm"
        allocation_5_days.action_approve()
        self.assertEqual(allocation_5_days.state, "validate")
        allocation_3_days.action_refuse()
        self.assertEqual(allocation_3_days.state, "refuse")

    def test_shortening_an_allocation_cannot_strand_taken_leaves(self):
        """Moving `date_to` back must be checked like reducing the days is.

        `write` only looked at the duration and the state, so an end date
        pulled in front of leaves already approved went through in silence and
        left them uncovered.
        """
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        leave_employee = self.env["hr.employee"].create(
            {"name": "Test Employee", "user_id": self.env.uid}
        )
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "5 days Allocation",
                "holiday_status_id": self.leave_type_paid.id,
                "number_of_days": 5,
                "employee_id": leave_employee.id,
                "date_from": start_of_week,
                "date_to": start_of_week + timedelta(days=30),
            }
        )
        allocation.action_approve()
        leave = self.env["hr.leave"].create(
            {
                "name": "Leave Request",
                "holiday_status_id": self.leave_type_paid.id,
                "request_date_from": start_of_week + timedelta(days=14),
                "request_date_to": start_of_week + timedelta(days=17),
                "employee_id": leave_employee.id,
            }
        )
        leave.action_approve()

        with self.assertRaises(ValidationError):
            allocation.date_to = start_of_week + timedelta(days=7)

    def test_allocation_end_date_stays_editable_once_validated(self):
        """The end date of a running allocation must be reachable.

        Extending or trimming the validity of an accrual allocation used to
        mean cancelling it and building a new one.
        """
        accrual_plan = self.env["hr.leave.accrual.plan"].create(
            {"name": "Accrual Plan", "time_off_type_id": self.leave_type_paid.id}
        )
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Accrued days",
                "holiday_status_id": self.leave_type_paid.id,
                "allocation_type": "accrual",
                "accrual_plan_id": accrual_plan.id,
                "number_of_days": 0,
                "employee_id": self.employee.id,
                "date_from": date(2022, 1, 1),
            }
        )
        allocation.action_approve()
        self.assertEqual(allocation.state, "validate")

        with Form(allocation) as allocation_form:
            self.assertFalse(
                allocation_form._get_modifier("date_to", "readonly"),
                "a validated accrual allocation should still let its end date move",
            )
            allocation_form.date_to = date(2023, 6, 30)
        self.assertEqual(allocation.date_to, date(2023, 6, 30))
