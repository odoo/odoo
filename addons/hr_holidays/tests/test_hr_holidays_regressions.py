from datetime import date, datetime
from unittest.mock import patch

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install")
class TestLeaveWriteGuards(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Strict Two Days",
                "requires_allocation": True,
                "request_unit": "day",
                "leave_validation_type": "hr",
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "allows_negative": False,
                "company_id": cls.company.id,
            }
        )

    def _allocate(self, days):
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Strict allocation",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": self.leave_type.id,
                "date_from": date(2026, 1, 1),
                "number_of_days": days,
            }
        )
        allocation.action_approve()
        return allocation

    def _one_day_leave(self, day):
        return self.env["hr.leave"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": day,
                "request_date_to": day,
            }
        )

    def test_extending_the_end_date_is_checked_against_the_allocation(self):
        self._allocate(2)
        leave = self._one_day_leave(date(2026, 9, 7))
        with self.assertRaises(
            ValidationError,
            msg="pushing request_date_to out to a full week must be refused "
            "against a 2-day allocation, exactly as pulling request_date_from "
            "back would be",
        ):
            leave.write({"request_date_to": date(2026, 9, 11)})

    def test_extending_the_start_date_is_checked_against_the_allocation(self):
        self._allocate(2)
        leave = self._one_day_leave(date(2026, 10, 9))
        with self.assertRaises(ValidationError):
            leave.write({"request_date_from": date(2026, 10, 5)})

    def test_write_does_not_mutate_the_caller_vals(self):
        self._allocate(20)
        leave = self._one_day_leave(date(2026, 11, 2))
        vals = {"date_from": leave.date_from}
        leave.write(vals)
        self.assertEqual(
            list(vals),
            ["date_from"],
            "write() injected request_date_from into the dict it was handed; a "
            "caller looping one dict over several records would carry it along",
        )

    def test_create_without_an_explicit_leave_type(self):
        self.leave_type.requires_allocation = False
        leave = (
            self.env["hr.leave"]
            .with_context(default_holiday_status_id=self.leave_type.id)
            .create(
                {
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": date(2026, 9, 21),
                    "request_date_to": date(2026, 9, 21),
                }
            )
        )
        self.assertTrue(leave.holiday_status_id)
        leave_without_type = self.env["hr.leave"].create(
            {
                "employee_id": self.employee_emp_id,
                "request_date_from": date(2026, 9, 22),
                "request_date_to": date(2026, 9, 22),
            }
        )
        self.assertTrue(leave_without_type.holiday_status_id)

    def test_stretching_an_hourly_leave_is_checked(self):
        lt = self.env["hr.leave.type"].create(
            {
                "name": "Strict Hours",
                "requires_allocation": True,
                "request_unit": "hour",
                "leave_validation_type": "hr",
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "allows_negative": False,
                "company_id": self.company.id,
            }
        )
        self.env["hr.leave.allocation"].create(
            {
                "name": "two hours",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": lt.id,
                "date_from": date(2026, 1, 1),
                "number_of_days": 0.25,
            }
        ).action_approve()
        leave = self.env["hr.leave"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": lt.id,
                "request_date_from": date(2027, 3, 1),
                "request_date_to": date(2027, 3, 1),
                "request_unit_hours": True,
                "request_hour_from": 8.0,
                "request_hour_to": 9.0,
            }
        )
        with self.assertRaises(
            ValidationError,
            msg="request_hour_to changes how much allocation the leave consumes, "
            "so widening it must be checked exactly as request_date_to is; a "
            "trigger list naming only the date fields let an hourly leave grow "
            "from 1h to 7.6h against a 2h allocation",
        ):
            leave.write({"request_hour_to": 17.0})

    def test_widening_a_half_day_leave_is_checked(self):
        lt = self.env["hr.leave.type"].create(
            {
                "name": "Strict Half Day",
                "requires_allocation": True,
                "request_unit": "half_day",
                "leave_validation_type": "hr",
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "allows_negative": False,
                "company_id": self.company.id,
            }
        )
        self.env["hr.leave.allocation"].create(
            {
                "name": "half a day",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": lt.id,
                "date_from": date(2026, 1, 1),
                "number_of_days": 0.5,
            }
        ).action_approve()
        leave = self.env["hr.leave"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": lt.id,
                "request_date_from": date(2027, 4, 1),
                "request_date_to": date(2027, 4, 1),
                "request_date_from_period": "am",
                "request_date_to_period": "am",
            }
        )
        self.assertEqual(leave.number_of_days, 0.5)
        with self.assertRaises(
            ValidationError,
            msg="flipping request_date_to_period from am to pm doubles the "
            "leave; the am/pm fields feed _compute_date_from_to and so must "
            "re-run the balance check",
        ):
            leave.write({"request_date_to_period": "pm"})

    def test_a_write_that_changes_nothing_skips_the_balance_check(self):
        self._allocate(2)
        leave = self._one_day_leave(date(2027, 5, 3))
        leave.write({"request_date_to": date(2027, 5, 3)})
        self.assertEqual(
            leave.number_of_days,
            1.0,
            "rewriting a date with the value it already holds changes no "
            "consumption, so the check must be skipped rather than re-run",
        )


@tagged("post_install", "-at_install")
class TestLeaveTypeBalances(TestHrHolidaysCommon):
    def test_two_types_sharing_a_name_keep_separate_balances(self):
        common_vals = {
            "requires_allocation": True,
            "request_unit": "day",
            "leave_validation_type": "hr",
            "allocation_validation_type": "no_validation",
            "employee_requests": True,
            "company_id": self.company.id,
        }
        first, second = self.env["hr.leave.type"].create(
            [
                {"name": "Paid Time Off", **common_vals},
                {"name": "Paid Time Off", **common_vals},
            ]
        )
        for leave_type, days in ((first, 20), (second, 7)):
            allocation = self.env["hr.leave.allocation"].create(
                {
                    "name": "alloc",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": days,
                }
            )
            allocation.action_approve()

        pair = (first + second).with_context(employee_id=self.employee_emp_id)
        self.assertEqual(
            pair.mapped("max_leaves"),
            [20.0, 7.0],
            "each leave type must report its own allocation, not the balance "
            "of the first type that happens to share its name",
        )


@tagged("post_install", "-at_install")
class TestAllocationApprovalActivity(TestHrHolidaysCommon):
    def test_activity_follows_the_allocation_validation_type(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Allocation needs HR, leaves do not",
                "requires_allocation": True,
                "request_unit": "day",
                "allocation_validation_type": "hr",
                "leave_validation_type": "no_validation",
                "employee_requests": True,
                "company_id": self.company.id,
                "responsible_ids": [(4, self.user_hruser_id)],
            }
        )
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "waiting for an officer",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": leave_type.id,
                "number_of_days": 1,
            }
        )
        self.assertEqual(allocation.state, "confirm")
        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", "hr.leave.allocation"),
                ("res_id", "=", allocation.id),
            ]
        )
        self.assertTrue(
            activities,
            "the allocation is waiting on an officer, so the officer needs an "
            "activity; keying off leave_validation_type suppressed it",
        )


@tagged("post_install", "-at_install")
class TestIsAbsentSearch(TestHrHolidaysCommon):
    def test_search_honours_the_searched_value(self):
        Employee = self.env["hr.employee"]
        absent = Employee._search_is_absent("in", [True])
        present = Employee._search_is_absent("in", [False])
        self.assertNotEqual(
            list(absent),
            list(present),
            "is_absent = False returned the same domain as is_absent = True, "
            "so the 'not absent' filter listed exactly the absent employees",
        )

    def test_public_employee_delegates_to_hr_employee(self):
        self.assertEqual(
            list(self.env["hr.employee"]._search_is_absent("in", [True])),
            list(self.env["hr.employee"]._search_is_absent("in", [True])),
        )


@tagged("post_install", "-at_install")
class TestAccrualLevelPeriodBounds(TestHrHolidaysCommon):
    def test_every_cadence_starts_its_period_on_the_previous_anchor(self):
        plan = self.env["hr.leave.accrual.plan"].create({"name": "Anchor plan"})
        level_vals = {
            "accrual_plan_id": plan.id,
            "added_value": 1,
            "added_value_type": "day",
            "start_count": 0,
            "milestone_date": "creation",
        }
        monthly, last_day, bimonthly, yearly = self.env[
            "hr.leave.accrual.level"
        ].create(
            [
                {**level_vals, "frequency": "monthly", "repeat_day": "20"},
                {**level_vals, "frequency": "monthly", "repeat_day": "last"},
                {
                    **level_vals,
                    "frequency": "bimonthly",
                    "repeat_day": "20",
                    "repeat_second_day": "25",
                },
                {
                    **level_vals,
                    "frequency": "yearly",
                    "repeat_month": "6",
                    "repeat_day": "20",
                },
            ]
        )
        last_call = date(2026, 3, 15)
        self.assertEqual(monthly._get_previous_anchor(last_call), date(2026, 2, 20))
        self.assertEqual(last_day._get_previous_anchor(last_call), date(2026, 3, 1))
        self.assertEqual(last_day._get_anchor_day(date(2026, 3, 1)), date(2026, 2, 28))
        self.assertEqual(bimonthly._get_previous_anchor(last_call), date(2026, 2, 25))
        self.assertEqual(yearly._get_previous_anchor(last_call), date(2025, 6, 20))


@tagged("post_install", "-at_install")
class TestConsumedLeavesExcess(TestHrHolidaysCommon):
    def test_two_leaves_ending_the_same_day_both_report_their_excess(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Hourly, one hour allocated",
                "requires_allocation": True,
                "request_unit": "hour",
                "leave_validation_type": "no_validation",
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "allows_negative": True,
                "max_allowed_negative": 100,
                "company_id": self.company.id,
            }
        )
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "one hour",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": leave_type.id,
                "date_from": date(2026, 1, 1),
                "number_of_days": 0.125,
            }
        )
        allocation.action_approve()

        day = date(2026, 9, 7)
        Leave = self.env["hr.leave"].with_context(leave_skip_date_check=True)
        morning, afternoon = (
            Leave.create(
                {
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": day,
                    "request_date_to": day,
                    "request_unit_hours": True,
                    "request_hour_from": hour_from,
                    "request_hour_to": hour_to,
                }
            )
            for hour_from, hour_to in ((8.0, 10.0), (13.0, 16.0))
        )

        _consumed, extra = self.employee_emp._get_consumed_leaves(leave_type, day)
        excess = extra[self.employee_emp][leave_type]["excess_days"]
        self.assertEqual(
            sorted(entry["leave_id"] for entry in excess.values()),
            sorted((morning + afternoon).ids),
            "both same-day leaves overran the allocation; keying excess_days "
            "by end date alone let the second overwrite the first",
        )


@tagged("post_install", "-at_install")
class TestApprovalRightsCacheKey(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager_type = cls.env["hr.leave.type"].create(
            {
                "name": "Manager Validated",
                "requires_allocation": False,
                "leave_validation_type": "manager",
                "company_id": cls.company.id,
            }
        )
        cls.leave = cls.env["hr.leave"].create(
            {
                "employee_id": cls.employee_emp_id,
                "holiday_status_id": cls.manager_type.id,
                "request_date_from": date(2026, 10, 5),
                "request_date_to": date(2026, 10, 5),
            }
        )

    def test_leave_rights_are_computed_per_user(self):
        as_manager = self.leave.with_user(self.user_responsible)
        as_employee = self.leave.with_user(self.user_employee)
        self.assertTrue(as_manager.can_validate)
        self.assertTrue(as_manager.can_refuse)
        self.assertFalse(
            as_employee.can_validate,
            "the employee must not inherit the approver's cached answer "
            "inside the same transaction",
        )
        self.assertFalse(as_employee.can_refuse)
        self.assertFalse(as_employee.can_approve)
        self.assertFalse(as_employee.can_back_to_approve)

    def test_allocation_rights_are_computed_per_user(self):
        allocation_type = self.env["hr.leave.type"].create(
            {
                "name": "Manager Allocated",
                "requires_allocation": True,
                "allocation_validation_type": "manager",
                "employee_requests": True,
                "company_id": self.company.id,
            }
        )
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "alloc",
                "employee_id": self.employee_emp_id,
                "holiday_status_id": allocation_type.id,
                "number_of_days": 2,
            }
        )
        as_manager = allocation.with_user(self.user_responsible)
        as_employee = allocation.with_user(self.user_employee)
        self.assertTrue(as_manager.can_validate)
        self.assertFalse(as_employee.can_validate)
        self.assertFalse(as_employee.can_refuse)


@tagged("post_install", "-at_install")
class TestLeaveWithoutDates(TestHrHolidaysCommon):
    def test_missing_request_dates_is_a_validation_error(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Dated",
                "requires_allocation": False,
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["hr.leave"].create(
                {
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": False,
                    "request_date_to": False,
                }
            )


@tagged("post_install", "-at_install")
class TestVersionCreateWithRpcDates(TestHrHolidaysCommon):
    def test_string_dates_are_accepted(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Plain",
                "requires_allocation": False,
                "company_id": self.company.id,
            }
        )
        self.env["hr.leave"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": leave_type.id,
                "request_date_from": date(2026, 11, 2),
                "request_date_to": date(2026, 11, 2),
            }
        )
        other_calendar = self.env["resource.calendar"].create(
            {"name": "Other", "company_id": self.company.id}
        )
        version = self.env["hr.version"].create(
            {
                "employee_id": self.employee_emp_id,
                "resource_calendar_id": other_calendar.id,
                "date_version": "2026-12-01",
                "contract_date_start": "2026-10-01",
            }
        )
        self.assertEqual(version.contract_date_start, date(2026, 10, 1))


@tagged("post_install", "-at_install")
class TestEmployeeDeletesOwnAllocation(TestHrHolidaysCommon):
    def test_pending_allocation_can_be_deleted_by_its_employee(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Requestable",
                "requires_allocation": True,
                "employee_requests": True,
                "allocation_validation_type": "hr",
                "company_id": self.company.id,
            }
        )
        allocation = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_employee)
            .create(
                {
                    "name": "mine",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 1,
                }
            )
        )
        self.assertEqual(allocation.state, "confirm")
        allocation.with_user(self.user_employee).unlink()
        self.assertFalse(allocation.exists())


@tagged("post_install", "-at_install")
class TestDurationComputesOnlyWhatItReads(TestHrHolidaysCommon):
    def test_hourly_type_skips_the_per_day_listing(self):
        hour_type = self.env["hr.leave.type"].create(
            {
                "name": "Hourly",
                "requires_allocation": False,
                "request_unit": "hour",
                "company_id": self.company.id,
            }
        )
        leave = self.env["hr.leave"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": hour_type.id,
                "request_date_from": date(2026, 10, 6),
                "request_date_to": date(2026, 10, 6),
                "request_hour_from": 9,
                "request_hour_to": 11,
            }
        )
        with patch.object(
            type(self.env["hr.employee"]),
            "_list_work_time_per_day",
            side_effect=AssertionError("per-day listing is not needed for hours"),
        ):
            _days, hours = leave._get_durations()[leave.id]
        self.assertEqual(hours, 2)


@tagged("post_install", "-at_install")
class TestBalanceUsesTheUsersToday(TestHrHolidaysCommon):
    @freeze_time("2026-09-04 23:30:00")
    def test_allocation_created_today_counts_today(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Today",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "company_id": self.company.id,
            }
        )
        ahead = (
            self.env["res.users"]
            .browse(self.env.uid)
            .with_context(tz="Europe/Brussels")
        )
        allocation = (
            self.env["hr.leave.allocation"]
            .with_env(ahead.env)
            .create(
                {
                    "name": "alloc",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 5,
                }
            )
        )
        allocation.action_approve()
        balance = leave_type.with_env(ahead.env).with_context(
            employee_id=self.employee_emp_id
        )
        self.assertEqual(
            balance.max_leaves,
            5,
            "an allocation dated the user's today must be in the balance even "
            "when UTC is still on the previous day",
        )


@tagged("post_install", "-at_install")
class TestAllocationActivitySkip(TestHrHolidaysCommon):
    def test_batch_context_creates_no_approval_activity(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Officer Allocated",
                "requires_allocation": True,
                "allocation_validation_type": "hr",
                "responsible_ids": [(4, self.user_hruser_id)],
                "company_id": self.company.id,
            }
        )
        allocation = (
            self.env["hr.leave.allocation"]
            .with_context(mail_activity_automation_skip=True)
            .create(
                {
                    "name": "batch",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 1,
                }
            )
        )
        self.assertFalse(
            allocation.activity_ids,
            "the batch wizard asks for no activities and must get none",
        )
        allocation.with_context(mail_activity_automation_skip=False).activity_update()
        self.assertEqual(allocation.activity_ids.user_id, self.user_hruser)


@tagged("post_install", "-at_install")
class TestDashboardConsumesLeavesOnce(TestHrHolidaysCommon):
    def test_allocation_data_reads_consumed_leaves_once(self):
        leave_types = self.env["hr.leave.type"].create(
            [
                {
                    "name": f"Dash {index}",
                    "requires_allocation": True,
                    "allocation_validation_type": "no_validation",
                    "employee_requests": True,
                    "company_id": self.company.id,
                }
                for index in range(3)
            ]
        )
        plan = self.env["hr.leave.accrual.plan"].create(
            {
                "name": "Dash plan",
                "level_ids": [
                    (
                        0,
                        0,
                        {
                            "added_value": 1,
                            "added_value_type": "day",
                            "frequency": "monthly",
                        },
                    )
                ],
            }
        )
        for leave_type in leave_types:
            for vals in (
                {"number_of_days": 5, "date_to": date(2027, 1, 31)},
                {
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                    "accrual_plan_id": plan.id,
                },
            ):
                self.env["hr.leave.allocation"].create(
                    {
                        "name": "dash",
                        "employee_id": self.employee_emp_id,
                        "holiday_status_id": leave_type.id,
                        "date_from": date(2026, 1, 1),
                        **vals,
                    }
                ).action_approve()
        Employee = type(self.env["hr.employee"])
        original = Employee._get_consumed_leaves
        calls = []

        def counting(employee, *args, **kwargs):
            calls.append(employee.ids)
            return original(employee, *args, **kwargs)

        with patch.object(Employee, "_get_consumed_leaves", counting):
            data = leave_types.get_allocation_data(self.employee_emp)
        self.assertEqual(len(data[self.employee_emp]), 3)
        self.assertEqual(
            len(calls),
            1,
            "simulating carry-over on the fake allocations must not recompute "
            "the consumed leaves once per leave type",
        )


@tagged("post_install", "-at_install")
class TestAllocationDescription(TestHrHolidaysCommon):
    """A description somebody wrote is theirs; a generated one keeps following."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Named Days",
                "requires_allocation": True,
                "request_unit": "day",
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "company_id": cls.company.id,
            }
        )

    def _allocate(self, **vals):
        return self.env["hr.leave.allocation"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": self.leave_type.id,
                "date_from": date(2026, 1, 1),
                "number_of_days": 5,
                **vals,
            }
        )

    def test_a_description_written_by_hand_survives_a_duration_change(self):
        allocation = self._allocate(name="Christmas bonus days")
        self.assertTrue(allocation.is_name_custom)
        allocation.write({"number_of_days": 7})
        self.assertEqual(
            allocation.name,
            "Christmas bonus days",
            "recomputing the generated title must not overwrite a description "
            "somebody typed; accrual runs write number_of_days every period",
        )

    def test_a_generated_description_still_follows_the_duration(self):
        allocation = self._allocate()
        self.assertFalse(allocation.is_name_custom)
        self.assertEqual(allocation.name, "Named Days (5.0 day(s))")
        allocation.write({"number_of_days": 7})
        self.assertEqual(allocation.name, "Named Days (7.0 day(s))")

    def test_writing_back_the_generated_title_is_not_a_rename(self):
        allocation = self._allocate()
        allocation.write({"name": allocation.name})
        self.assertFalse(
            allocation.is_name_custom,
            "a form that echoes the onchange-filled description back on save "
            "has not renamed anything",
        )
        allocation.write({"number_of_days": 7})
        self.assertEqual(allocation.name, "Named Days (7.0 day(s))")

    def test_clearing_the_description_hands_it_back_to_the_generator(self):
        allocation = self._allocate(name="Mine")
        allocation.write({"name": False})
        self.assertFalse(allocation.is_name_custom)
        allocation.write({"number_of_days": 7})
        self.assertEqual(allocation.name, "Named Days (7.0 day(s))")


@tagged("post_install", "-at_install")
class TestLeaveTypeBalanceSearch(TestHrHolidaysCommon):
    """A search on a balance must select what the compute would report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hour_type = cls.env["hr.leave.type"].create(
            {
                "name": "Hourly Balance",
                "requires_allocation": True,
                "request_unit": "hour",
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "company_id": cls.company.id,
            }
        )
        cls.env["hr.leave.allocation"].create(
            {
                "employee_id": cls.employee_emp_id,
                "holiday_status_id": cls.hour_type.id,
                "date_from": date(2026, 1, 1),
                "number_of_days": 2,
            }
        ).action_approve()

    def test_an_hourly_type_is_searched_in_the_unit_it_reports(self):
        leave_types = self.env["hr.leave.type"].with_context(
            employee_id=self.employee_emp_id
        )
        balance = leave_types.browse(self.hour_type.id).max_leaves
        self.assertGreater(
            balance,
            2,
            "two days of an hourly type report as hours, not as days",
        )
        self.assertIn(
            self.hour_type,
            leave_types.search([("max_leaves", ">", 3)]),
            "the search summed the allocation in days while the field reports "
            "hours, so it missed a type whose balance is %s" % balance,
        )

    def test_a_type_with_no_allocation_has_a_zero_balance_to_be_found(self):
        unallocated = self.env["hr.leave.type"].create(
            {
                "name": "Never Allocated",
                "requires_allocation": True,
                "company_id": self.company.id,
            }
        )
        leave_types = self.env["hr.leave.type"].with_context(
            employee_id=self.employee_emp_id
        )
        self.assertEqual(leave_types.browse(unallocated.id).max_leaves, 0)
        self.assertIn(
            unallocated,
            leave_types.search([("max_leaves", "<=", 0)]),
            "a type with no allocation row still has a balance, and it is zero",
        )

    def test_a_search_without_an_employee_in_context_is_not_empty(self):
        leave_types = self.env["hr.leave.type"].with_context(employee_id=False)
        self.assertTrue(
            leave_types.search([("max_leaves", ">=", 0)]),
            "with no employee to read a balance for, every balance is zero -- "
            "which is >= 0, not 'no type matches'",
        )


@tagged("post_install", "-at_install")
class TestBackToWorkDate(TestHrHolidaysCommon):
    """`leave_date_to` is the first moment the employee works again."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.company.resource_calendar_id
        cls.idle_calendar = cls.env["resource.calendar"].create(
            {
                "name": "No attendance at all",
                "tz": cls.calendar.tz,
                "company_id": cls.company.id,
                "attendance_ids": [],
            }
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Back To Work",
                "requires_allocation": False,
                "leave_validation_type": "no_validation",
                "company_id": cls.company.id,
            }
        )

    def _employee_with_two_calendar_periods(self):
        employee = self.env["hr.employee"].create(
            {"name": "Two schedules", "company_id": self.company.id}
        )
        employee.version_id.write(
            {
                "date_version": date(2026, 3, 1),
                "contract_date_start": date(2026, 3, 1),
                "resource_calendar_id": self.calendar.id,
            }
        )
        employee.create_version(
            {
                "date_version": date(2026, 3, 4),
                "resource_calendar_id": self.idle_calendar.id,
            }
        )
        return employee

    def test_the_first_working_interval_comes_from_the_first_period(self):
        employee = self._employee_with_two_calendar_periods()
        back_on = employee._get_first_working_interval(datetime(2026, 3, 2, 12, 0))
        self.assertIsNotNone(
            back_on,
            "Monday 2026-03-02 is a working day on the first period's calendar; "
            "answering from the last period instead reports the employee as "
            "never coming back",
        )
        self.assertEqual(back_on.date(), date(2026, 3, 2))

    @freeze_time("2026-03-04 10:00:00")
    def test_every_employee_is_asked_of_its_calendar_once(self):
        employees = self.env["hr.employee"].create(
            [
                {"name": f"Absent {index}", "company_id": self.company.id}
                for index in range(5)
            ]
        )
        self.env["hr.leave"].with_context(leave_skip_date_check=True).create(
            [
                {
                    "employee_id": employee.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": date(2026, 3, 2),
                    "request_date_to": date(2026, 3, 6),
                }
                for employee in employees
            ]
        )
        self.env.flush_all()
        employees.invalidate_recordset()
        Calendar = type(self.env["resource.calendar"])
        original = Calendar._work_intervals_batch
        calls = []

        def counting(calendar, *args, **kwargs):
            calls.append(calendar.ids)
            return original(calendar, *args, **kwargs)

        with patch.object(Calendar, "_work_intervals_batch", counting):
            employees.mapped("leave_date_to")
        self.assertEqual(
            len(calls),
            1,
            "five employees sharing one calendar are one batched question, not "
            "one call each",
        )

    def test_the_batch_reports_what_it_answered(self):
        employee = self._employee_with_two_calendar_periods()
        with self.assertLogs(
            "odoo.addons.hr_holidays.debug.logic", level="DEBUG"
        ) as captured:
            employee._get_first_working_interval(datetime(2026, 3, 2, 12, 0))
        self.assertTrue(
            any(
                "_get_first_working_interval_batch" in line
                and "answered 1 of 1" in line
                for line in captured.output
            ),
            captured.output,
        )


@tagged("post_install", "-at_install")
class TestVersionLeaveWindow(TestHrHolidaysCommon):
    def test_a_version_without_contract_dates_bounds_nothing(self):
        contracted = self.env["hr.employee"].create(
            {"name": "Under contract", "company_id": self.company.id}
        )
        contracted.version_id.write(
            {
                "contract_date_start": date(2026, 1, 1),
                "contract_date_end": date(2026, 6, 30),
            }
        )
        uncontracted = self.env["hr.employee"].create(
            {"name": "No contract", "company_id": self.company.id}
        )
        versions = contracted.version_id | uncontracted.version_id
        self.assertFalse(uncontracted.version_id.contract_date_start)
        leaves = versions._get_leaves()
        self.assertEqual(
            leaves,
            self.env["hr.leave"],
            "a version with no contract start contributes no window; taking the "
            "min over it compares a date with False",
        )

    def test_no_contracted_version_searches_nothing(self):
        employee = self.env["hr.employee"].create(
            {"name": "Still no contract", "company_id": self.company.id}
        )
        self.assertEqual(employee.version_id._get_leaves(), self.env["hr.leave"])


@tagged("post_install", "-at_install")
class TestRequestDatesGoTogether(TestHrHolidaysCommon):
    def test_clearing_one_request_date_clears_the_whole_period(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Both Ends",
                "requires_allocation": False,
                "leave_validation_type": "no_validation",
                "company_id": self.company.id,
            }
        )
        leave = self.env["hr.leave"].new(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": leave_type.id,
                "request_date_from": date(2026, 4, 6),
                "request_date_to": date(2026, 4, 8),
            }
        )
        self.assertTrue(leave.date_from and leave.date_to)
        leave.request_date_to = False
        self.assertFalse(
            leave.date_from,
            "a request with only a start date has no period; keeping date_from "
            "leaves a leave that starts and never ends",
        )
        self.assertFalse(leave.date_to)


@tagged("post_install", "-at_install")
class TestPresenceFollowsTheLeave(TestHrHolidaysCommon):
    """Approving a leave changes the presence the same request reads back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Presence Leaves",
                "time_type": "leave",
                "requires_allocation": False,
                "leave_validation_type": "hr",
                "company_id": cls.company.id,
            }
        )

    def _leave_covering_now(self):
        return self.env["hr.leave"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": date(2026, 3, 2),
                "request_date_to": date(2026, 3, 6),
            }
        )

    @freeze_time("2026-03-04 10:00:00")
    def test_the_presence_icon_is_invalidated_by_the_approval(self):
        employee = self.employee_emp
        self.assertNotIn("holiday", employee.hr_icon_display)
        self._leave_covering_now().action_approve()
        self.assertTrue(employee.is_absent)
        self.assertIn(
            "holiday",
            employee.hr_icon_display,
            "hr_icon_display is read straight after the approval that made the "
            "employee absent; without a declared dependency on is_absent it "
            "answers from the cache the approval never invalidated",
        )

    @freeze_time("2026-03-04 10:00:00")
    def test_the_presence_state_is_invalidated_by_the_approval(self):
        employee = self.employee_emp
        employee.hr_presence_state
        self._leave_covering_now().action_approve()
        self.assertEqual(employee.hr_presence_state, "absent")
