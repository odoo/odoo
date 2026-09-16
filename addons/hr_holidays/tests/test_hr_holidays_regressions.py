import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from odoo.addons.base.models.ir_module import Manifest
from odoo.addons.hr_holidays.models.hr_employee import HrEmployee
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.addons.mail.tests.common import mail_new_test_user

_logger = logging.getLogger(__name__)


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

    def test_an_employee_already_at_work_is_back_at_that_moment(self):
        """And the answer must not depend on where the batch began."""
        employees = self.env["hr.employee"].create(
            [
                {"name": f"Midshift {index}", "company_id": self.company.id}
                for index in range(2)
            ]
        )
        # The calendar is Brussels, so on 2026-03-02 (CET) the morning runs
        # 07:00-11:00 UTC. One employee asks from its very start, the other
        # from the middle of it -- near enough to share a batch, which is the
        # case where nothing clips the interval to the second one's question.
        shift_start = datetime(2026, 3, 2, 7, 0)
        midshift = datetime(2026, 3, 2, 9, 0)
        together = employees._get_first_working_interval_batch(
            {
                employees[0].id: shift_start,
                employees[1].id: midshift,
            }
        )
        self.assertEqual(
            together[employees[0].id].astimezone(UTC).replace(tzinfo=None),
            shift_start,
        )
        self.assertEqual(
            together[employees[1].id].astimezone(UTC).replace(tzinfo=None),
            midshift,
            "asked at a moment the employee is working, the answer is that "
            "moment, not the start of the shift they are already in -- and not "
            "the next shift, which is what reading the interval's own beginning "
            "gives once a batch-mate's earlier question stopped it being clipped",
        )
        self.assertEqual(
            together[employees[1].id],
            employees[1]._get_first_working_interval(midshift),
            "who else is in the batch cannot change an employee's answer",
        )

    @freeze_time("2026-03-04 10:00:00")
    def test_distant_dates_do_not_widen_one_anothers_window(self):
        employees = self.env["hr.employee"].create(
            [
                {"name": f"Spread {index}", "company_id": self.company.id}
                for index in range(3)
            ]
        )
        starts = {
            employees[0].id: datetime(2026, 3, 2, 9, 0),
            employees[1].id: datetime(2026, 9, 2, 9, 0),
            employees[2].id: datetime(2027, 3, 2, 9, 0),
        }
        Calendar = type(self.env["resource.calendar"])
        original = Calendar._work_intervals_batch
        windows = []

        def recording(calendar, start, end, *args, **kwargs):
            windows.append((end - start).days)
            return original(calendar, start, end, *args, **kwargs)

        with patch.object(Calendar, "_work_intervals_batch", recording):
            answers = employees._get_first_working_interval_batch(starts)
        self.assertEqual(len(answers), 3)
        self.assertTrue(all(answers.values()), answers)
        self.assertTrue(
            all(span <= 14 for span in windows),
            "one employee whose leave ends a year out must not make the others "
            "pay for a year of attendance intervals to answer a seven-day "
            "question; spans asked were %s" % windows,
        )

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
        """On the campaign's shared channel, in the campaign's line shape.

        `odoo.debug.<channel>.<scope>` and `event=<name> k=v` are fixed by
        `odoo.libs.debug_log` so one grep finds a site on both the Python and
        the JS side, and so the strip pass at the end of the campaign has one
        vocabulary to remove rather than one per module.
        """
        employee = self._employee_with_two_calendar_periods()
        with self.assertLogs(
            "odoo.debug.logic.hr_holidays.hr_employee", level="DEBUG"
        ) as captured:
            employee._get_first_working_interval(datetime(2026, 3, 2, 12, 0))
        self.assertTrue(
            any(
                "event=first_working_interval_batch" in line
                and "answered=1" in line
                and "pending=1" in line
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

    def test_both_presence_computes_declare_what_they_read(self):
        """This module's own overrides say they read `is_absent`.

        Asserted on the class rather than on `registry.field_depends`, which is
        the union every installed module contributes: a sibling declaring the
        same path would keep that green with this module's declaration deleted,
        and on a database carrying hr_presence one of these two is exactly that
        case. The behavioural test above covers the icon; `hr_presence_state`
        is reached through `user_id.im_status`, invalidated often enough that
        no behavioural test of it can fail.
        """
        for compute in (
            HrEmployee._compute_presence_icon,
            HrEmployee._compute_hr_presence_state,
        ):
            self.assertIn(
                "is_absent",
                getattr(compute, "_depends", ()),
                "%s reads is_absent and must declare it here, whether or not "
                "some other module happens to declare it too" % compute.__name__,
            )

    def test_both_presence_fields_are_invalidated_by_it(self):
        """And the declaration reaches the field the client reads."""
        for field_name in ("hr_icon_display", "hr_presence_state"):
            field = self.env["hr.employee"]._fields[field_name]
            self.assertIn(
                "is_absent",
                self.env.registry.field_depends[field],
                "%s must be invalidated when is_absent changes" % field_name,
            )


@tagged("post_install", "-at_install")
class TestOverlapWarning(TestHrHolidaysCommon):
    """The text the form shows when a period is already taken."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Overlapping",
                "requires_allocation": False,
                "leave_validation_type": "hr",
                "allow_request_on_top": False,
                "company_id": cls.company.id,
            }
        )

    def _request(self, employee, user=None):
        leaves = self.env["hr.leave"].with_context(leave_skip_date_check=True)
        if user:
            leaves = leaves.with_user(user)
        return leaves.create(
            {
                "employee_id": employee.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": date(2026, 3, 4),
                "request_date_to": date(2026, 3, 4),
            }
        )

    def test_someone_elses_time_off_is_reported_in_the_third_person(self):
        subject = self._request(self.employee_hruser)
        self._request(self.employee_hruser)
        self._request(self.employee_hruser)
        subject.invalidate_recordset(["dashboard_warning_message"])
        message = subject.dashboard_warning_message
        self.assertTrue(
            message.startswith("An employee already booked time off"), message
        )
        self.assertIn("Armande HrUser", message)
        self.assertEqual(
            message.count("\n\t"),
            1,
            "two identical bookings by one employee are one line, not two: %r"
            % message,
        )

    def test_the_warning_only_ever_looks_at_the_requester(self):
        """It says "an employee", and it means this one.

        The conflict search is bounded by `self.employee_id`, so the third
        person in the message is about who is reading it, not about a second
        employee. A colleague off on the same day is not a conflict here.
        """
        subject = self._request(self.employee_emp)
        self._request(self.employee_hruser)
        subject.invalidate_recordset(["dashboard_warning_message"])
        self.assertFalse(subject.dashboard_warning_message)

    def test_your_own_time_off_is_reported_in_the_first_person(self):
        subject = self._request(self.employee_emp, user=self.user_employee)
        self._request(self.employee_emp, user=self.user_employee)
        subject.invalidate_recordset(["dashboard_warning_message"])
        message = subject.with_user(self.user_employee).dashboard_warning_message
        self.assertTrue(message.startswith("You've already booked time off"), message)
        self.assertNotIn(
            "David Employee",
            message,
            "your own name is not worth telling you: %r" % message,
        )

    def test_a_request_with_nothing_against_it_says_nothing(self):
        subject = self._request(self.employee_emp)
        subject.invalidate_recordset(["dashboard_warning_message"])
        self.assertFalse(subject.dashboard_warning_message)


@tagged("post_install", "-at_install")
class TestFlexibleRequestDuration(TestHrHolidaysCommon):
    """A resource with no timetable still has a morning and an afternoon."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.flexible_calendar = cls.env["resource.calendar"].create(
            {
                "name": "Flexible 40h",
                "tz": "UTC",
                "company_id": cls.company.id,
                "flexible_hours": True,
                "hours_per_day": 8,
                "full_time_required_hours": 40,
            }
        )
        cls.standard_calendar = cls.env["resource.calendar"].create(
            {
                "name": "Standard for comparison",
                "tz": "UTC",
                "company_id": cls.company.id,
            }
        )
        cls.half_day_type = cls.env["hr.leave.type"].create(
            {
                "name": "Flexible Halves",
                "requires_allocation": False,
                "request_unit": "half_day",
                "leave_validation_type": "hr",
                "company_id": cls.company.id,
            }
        )
        cls.flexible = cls.env["hr.employee"].create(
            {
                "name": "No timetable",
                "company_id": cls.company.id,
                "resource_calendar_id": cls.flexible_calendar.id,
            }
        )
        cls.standard = cls.env["hr.employee"].create(
            {
                "name": "Fixed timetable",
                "company_id": cls.company.id,
                "resource_calendar_id": cls.standard_calendar.id,
            }
        )

    def _request(self, employee, date_from, date_to, period_from, period_to):
        return (
            self.env["hr.leave"]
            .with_context(leave_skip_date_check=True)
            .new(
                {
                    "employee_id": employee.id,
                    "holiday_status_id": self.half_day_type.id,
                    "request_date_from": date_from,
                    "request_date_to": date_to,
                    "request_date_from_period": period_from,
                    "request_date_to_period": period_to,
                }
            )
        )

    def test_a_half_day_at_each_end_costs_one_day_either_way(self):
        self.assertTrue(self.flexible.is_flexible)
        shapes = [
            ((date(2026, 3, 2), date(2026, 3, 3)), ("pm", "am")),
            ((date(2026, 3, 2), date(2026, 3, 4)), ("pm", "am")),
            ((date(2026, 3, 2), date(2026, 3, 4)), ("am", "pm")),
            ((date(2026, 3, 2), date(2026, 3, 2)), ("am", "am")),
            ((date(2026, 3, 2), date(2026, 3, 2)), ("pm", "pm")),
            ((date(2026, 3, 2), date(2026, 3, 2)), ("am", "pm")),
        ]
        for (date_from, date_to), (period_from, period_to) in shapes:
            with self.subTest(dates=(date_from, date_to), periods=period_to):
                flexible = self._request(
                    self.flexible, date_from, date_to, period_from, period_to
                )
                standard = self._request(
                    self.standard, date_from, date_to, period_from, period_to
                )
                self.assertEqual(
                    (flexible.number_of_days, flexible.number_of_hours),
                    (standard.number_of_days, standard.number_of_hours),
                    "a half at each end is a half at each end whether or not "
                    "the employee has a schedule; reading the request's day "
                    "count and ignoring its periods charges a whole day for a "
                    "morning",
                )

    def test_every_day_of_a_part_day_request_gives_up_its_own_half(self):
        leave = self.env["hr.leave"].create(
            {
                "employee_id": self.flexible.id,
                "holiday_status_id": self.half_day_type.id,
                "request_date_from": date(2026, 3, 2),
                "request_date_to": date(2026, 3, 3),
                "request_date_from_period": "pm",
                "request_date_to_period": "am",
            }
        )
        leave.action_approve()
        resource_leave = self.env["resource.schedule.exception"].search(
            [("holiday_id", "=", leave.id)]
        )
        self.assertTrue(resource_leave)
        removed = []
        charged = defaultdict(lambda: defaultdict(float))
        self.flexible.resource_id._format_leave(
            (
                resource_leave.date_from.replace(tzinfo=UTC),
                resource_leave.date_to.replace(tzinfo=UTC),
                resource_leave,
            ),
            charged,
            defaultdict(lambda: defaultdict(float)),
            removed,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        self.assertEqual(
            [(start.date(), start.hour, stop.hour) for start, stop, _ in removed],
            [(date(2026, 3, 2), 12, 23), (date(2026, 3, 3), 0, 12)],
            "the afternoon of the first day and the morning of the second, not "
            "one window on the first day built from the first day's period",
        )
        self.assertEqual(
            dict(charged[self.flexible.resource_id.id]),
            {date(2026, 3, 2): -4.0, date(2026, 3, 3): -4.0},
            "four hours on each day it touches, not eight on the first",
        )


@tagged("post_install", "-at_install")
class TestRefusalIsNotAnApproval(TestHrHolidaysCommon):
    """The two approver fields hold whoever validated, and a refuser did not."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Two Step",
                "requires_allocation": False,
                "leave_validation_type": "both",
                "company_id": cls.company.id,
            }
        )
        cls.allocation_type = cls.env["hr.leave.type"].create(
            {
                "name": "Two Step Allocation",
                "requires_allocation": True,
                "allocation_validation_type": "hr",
                "employee_requests": True,
                "company_id": cls.company.id,
            }
        )

    def _leave(self):
        return (
            self.env["hr.leave"]
            .with_context(leave_skip_date_check=True)
            .create(
                {
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": date(2026, 3, 4),
                    "request_date_to": date(2026, 3, 4),
                }
            )
        )

    def test_refusing_a_request_nobody_approved_records_no_approver(self):
        leave = self._leave()
        leave.with_user(self.user_hrmanager).action_refuse()
        self.assertEqual(leave.state, "refuse")
        self.assertFalse(
            leave.second_approver_id,
            "a leave that went straight from To Approve to Refused was never "
            "given a second approval, and the form says it was",
        )
        self.assertFalse(leave.first_approver_id)

    def test_refusing_after_a_first_approval_keeps_the_first_approver(self):
        leave = self._leave()
        leave.with_user(self.user_responsible).action_approve()
        self.assertEqual(leave.state, "validate1")
        self.assertEqual(leave.first_approver_id, self.employee_responsible)
        leave.with_user(self.user_hrmanager).action_refuse()
        self.assertEqual(leave.state, "refuse")
        self.assertEqual(
            leave.first_approver_id,
            self.employee_responsible,
            "whoever really gave the first approval stays on record when "
            "somebody else refuses it later",
        )

    def test_refusing_an_allocation_keeps_its_approver(self):
        allocation = self.env["hr.leave.allocation"].create(
            {
                "employee_id": self.employee_emp_id,
                "holiday_status_id": self.allocation_type.id,
                "date_from": date(2026, 1, 1),
                "number_of_days": 3,
            }
        )
        allocation.with_user(self.user_hruser).action_approve()
        self.assertEqual(allocation.approver_id, self.employee_hruser)
        allocation.with_user(self.user_hrmanager).action_refuse()
        self.assertEqual(allocation.state, "refuse")
        self.assertEqual(
            allocation.approver_id,
            self.employee_hruser,
            "refusing must not rewrite who approved it",
        )


@tagged("post_install", "-at_install")
class TestCreatingManyRequests(TestHrHolidaysCommon):
    """A wizard generating a company's leaves creates hundreds in one call."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Batch Created",
                "requires_allocation": False,
                "leave_validation_type": "hr",
                "company_id": cls.company.id,
            }
        )
        cls.employees = cls.env["hr.employee"].create(
            [
                {"name": f"Batch {index}", "company_id": cls.company.id}
                for index in range(20)
            ]
        )

    def _create(self, count):
        return (
            self.env["hr.leave"]
            .with_context(leave_skip_date_check=True)
            .create(
                [
                    {
                        "employee_id": self.employees[index].id,
                        "holiday_status_id": self.leave_type.id,
                        "request_date_from": date(2026, 3, 2),
                        "request_date_to": date(2026, 3, 2),
                    }
                    for index in range(count)
                ]
            )
        )

    def _statements_to_create(self, count):
        """Statements, not rows: one INSERT of twenty rows is one question, and
        `sql_log_count` would read it as twenty."""
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        self._create(count)
        self.env.flush_all()
        return self.env.cr.sql_statement_count - before

    def test_the_cost_does_not_grow_with_the_number_of_requests(self):
        self._statements_to_create(5)  # warm what the first call of anything warms
        few = self._statements_to_create(5)
        many = self._statements_to_create(20)
        self.assertEqual(
            many,
            few,
            "creating twenty requests on one calendar and one date must cost "
            "what creating five does; asking the attendances once per request "
            "made it grow with the batch -- %s statements against %s" % (many, few),
        )

    def test_one_calendar_and_one_date_are_asked_once_per_batch(self):
        Calendar = type(self.env["resource.calendar"])
        original = Calendar._get_hours_for_date
        asked = []

        def recording(calendar, day, day_period=None):
            asked.append((calendar.id, day, day_period))
            return original(calendar, day, day_period)

        with patch.object(Calendar, "_get_hours_for_date", recording):
            self._create(5)
            self.env.flush_all()
            after_five = len(asked)
            self._create(20)
            self.env.flush_all()
            after_twenty = len(asked) - after_five
        self.assertEqual(
            after_twenty,
            after_five,
            "the working hours of a day are a property of the calendar and the "
            "day, so a batch sharing both asks the same number of times "
            "whatever its size: %s for twenty against %s for five"
            % (after_twenty, after_five),
        )


@tagged("post_install", "-at_install")
class TestContextualEmployee(TestHrHolidaysCommon):
    """One key, two shapes, and everything downstream wants one employee."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Contextual",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "employee_requests": True,
                "company_id": cls.company.id,
            }
        )
        cls.env["hr.leave.allocation"].create(
            {
                "holiday_status_id": cls.leave_type.id,
                "employee_id": cls.employee_emp_id,
                "date_from": date(2026, 1, 1),
                "number_of_days": 12,
            }
        ).action_approve()

    def test_the_dashboard_action_sends_a_shape_the_dashboard_accepts(self):
        employees = self.employee_emp | self.employee_hruser
        context = employees.action_time_off_dashboard()["context"]
        data = (
            self.env["hr.employee"]
            .with_context(**context)
            .get_time_off_dashboard_data()
        )
        self.assertTrue(
            data["allocation_data"],
            "the action hands its whole selection to the dashboard, which reads "
            "a balance and so needs one employee: %s" % context,
        )

    def test_either_shape_names_the_same_employee(self):
        Employee = self.env["hr.employee"]
        for shape in (
            self.employee_emp_id,
            [self.employee_emp_id],
            [self.employee_emp_id, self.employee_hruser_id],
        ):
            with self.subTest(shape=shape):
                self.assertEqual(
                    Employee.with_context(employee_id=shape)._get_contextual_employee(),
                    self.employee_emp,
                )

    def test_no_employee_in_context_falls_back_to_the_user(self):
        Employee = self.env["hr.employee"]
        self.assertEqual(
            Employee.with_context(employee_id=None)._get_contextual_employee(),
            self.env.user.employee_id[:1],
        )
        self.assertFalse(
            Employee.with_context(employee_id=False)._get_contextual_employee()
        )


@tagged("post_install", "-at_install")
class TestLeaveStatusesTravelWithTheMemberList(TestHrHolidaysCommon):
    """Wherever a client sorts members into online and offline, it must know
    what a leave status means.

    `res.partner._compute_presence` decorates `im_status` for every client, so
    a bundle that renders the member list without this module's
    `onlineMemberStatuses` patch puts an employee who is online but on leave
    under Offline.
    """

    PARTITIONING_PATH = "mail/static/src/discuss/core/common/thread_model_patch.js"
    VOCABULARY_PATH = "hr_holidays/static/src/store_service_patch.js"

    def _bundles_containing(self, path):
        """Every assembled bundle whose expanded contents include `path`."""
        IrAsset = self.env["ir.asset"]
        params = IrAsset._prepare_assets_params()
        installed = set(
            self.env["ir.module.module"]
            .search([("state", "=", "installed")])
            .mapped("name")
        )
        bundles = set(IrAsset.search([]).mapped("bundle"))
        for manifest in Manifest.get_all_addon_manifests():
            if manifest.name in installed:
                bundles.update(manifest.get("assets") or {})
        found = set()
        for bundle in sorted(bundles):
            try:
                entries = IrAsset._get_asset_paths(bundle, params)
            except Exception as exc:
                _logger.info("skipping bundle %s: %s", bundle, exc)
                continue
            if any(entry.path.lstrip("/") == path for entry in entries):
                found.add(bundle)
        return found

    def test_every_bundle_that_partitions_members_knows_the_leave_statuses(self):
        partitioning = self._bundles_containing(self.PARTITIONING_PATH)
        self.assertTrue(
            partitioning,
            "could not find the bundles carrying %s" % self.PARTITIONING_PATH,
        )
        vocabulary = self._bundles_containing(self.VOCABULARY_PATH)
        self.assertFalse(
            partitioning - vocabulary,
            "%s sort members with mail's onlineMemberStatuses but never learn "
            "that leave_online, leave_away and leave_busy are online, so an "
            "employee on leave shows as offline there"
            % sorted(partitioning - vocabulary),
        )


@tagged("post_install", "-at_install")
class TestReportDoesNotLeakTheDescription(TestHrHolidaysCommon):
    """A leave's description is private, and a report is a second way in."""

    SECRET = "Chemotherapy session"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Private Reasons",
                "requires_allocation": False,
                "leave_validation_type": "hr",
                "company_id": cls.company.id,
            }
        )
        # A department manager who is neither an officer nor anybody's approver.
        cls.department = cls.env["hr.department"].create(
            {"name": "Reporting dept", "company_id": cls.company.id}
        )
        cls.onlooker = mail_new_test_user(
            cls.env, login="onlooker", groups="base.group_user"
        )
        cls.department.manager_id = cls.env["hr.employee"].create(
            {
                "name": "Department Manager",
                "user_id": cls.onlooker.id,
                "company_id": cls.company.id,
                "department_id": cls.department.id,
            }
        )
        cls.subject = cls.env["hr.employee"].create(
            {
                "name": "Reporting Subject",
                "company_id": cls.company.id,
                "department_id": cls.department.id,
            }
        )
        cls.leave = (
            cls.env["hr.leave"]
            .with_context(leave_skip_date_check=True)
            .create(
                {
                    "employee_id": cls.subject.id,
                    "holiday_status_id": cls.leave_type.id,
                    "name": cls.SECRET,
                    "request_date_from": date(2026, 3, 2),
                    "request_date_to": date(2026, 3, 2),
                }
            )
        )

    def _report_rows(self, user):
        self.env.flush_all()
        return (
            self.env["hr.leave.report"]
            .with_user(user)
            .search([("leave_id", "=", self.leave.id)])
        )

    def test_a_department_manager_sees_the_row_and_not_the_reason(self):
        self.assertFalse(self.onlooker.has_group("hr_holidays.group_hr_holidays_user"))
        self.assertNotEqual(self.subject.leave_manager_id, self.onlooker)
        rows = self._report_rows(self.onlooker)
        self.assertTrue(
            rows, "the department manager is meant to see that the leave exists"
        )
        with self.assertRaises(
            AccessError,
            msg="hr.leave hides the description from this user, and reading the "
            "same column through the report must not hand it over",
        ):
            rows.mapped("name")

    def test_an_officer_still_reads_it(self):
        rows = self._report_rows(self.user_hruser)
        self.assertEqual(rows.mapped("name"), [self.SECRET])


@tagged("post_install", "-at_install")
class TestGeneratedTimeOffWaitsForApproval(TestHrHolidaysCommon):
    """Generating time off in bulk must not book what nobody approved."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Needs An Officer",
                "requires_allocation": False,
                "leave_validation_type": "hr",
                "company_id": cls.company.id,
            }
        )
        cls.team = cls.env["hr.employee"].create(
            [
                {
                    "name": f"Shutdown {index}",
                    "company_id": cls.company.id,
                    "leave_manager_id": cls.user_responsible.id,
                }
                for index in range(3)
            ]
        )

    def _generate(self, user):
        wizard = (
            self.env["hr.leave.generate.multi.wizard"]
            .with_user(user)
            .create(
                {
                    "name": "Team shutdown",
                    "holiday_status_id": self.leave_type.id,
                    "allocation_mode": "employee",
                    "employee_ids": [Command.set(self.team.ids)],
                    "date_from": date(2026, 3, 2),
                    "date_to": date(2026, 3, 4),
                }
            )
        )
        return self.env["hr.leave"].browse(
            wizard.action_generate_time_off()["domain"][0][2]
        )

    def _resource_leaves(self, leaves):
        return self.env["resource.schedule.exception"].search(
            [("holiday_id", "in", leaves.ids)]
        )

    def test_pending_requests_reserve_nothing_until_they_are_approved(self):
        self.assertFalse(
            self.user_responsible.has_group("hr_holidays.group_hr_holidays_user")
        )
        leaves = self._generate(self.user_responsible)
        self.assertEqual(set(leaves.mapped("state")), {"confirm"})
        self.assertFalse(
            self._resource_leaves(leaves),
            "a request still waiting for an officer must not book the "
            "employee's working time",
        )
        self.assertFalse(
            leaves.mapped("meeting_id"),
            "nor put a meeting in their calendar",
        )

    def test_approving_them_reserves_the_period_exactly_once(self):
        leaves = self._generate(self.user_responsible)
        leaves.with_user(self.user_hruser).action_approve()
        self.assertEqual(set(leaves.mapped("state")), {"validate"})
        self.assertEqual(
            len(self._resource_leaves(leaves)),
            len(leaves),
            "applying the request at generation and again at approval booked "
            "the same period twice, and the working-time engine subtracts both",
        )

    def test_an_officer_generating_them_reserves_the_period_once(self):
        leaves = self._generate(self.user_hruser)
        self.assertEqual(set(leaves.mapped("state")), {"validate"})
        self.assertEqual(len(self._resource_leaves(leaves)), len(leaves))


@tagged("post_install", "-at_install")
class TestScheduleChangeRepricesFutureLeave(TestHrHolidaysCommon):
    """Changing an employee's working schedule re-prices the leave they have
    already been granted for after it, and books it exactly once."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.full_time = cls.company.resource_calendar_id
        cls.mornings = cls.env["resource.calendar"].create(
            {
                "name": "Mornings only",
                "tz": cls.full_time.tz,
                "company_id": cls.company.id,
                "attendance_ids": [
                    Command.create(
                        {
                            "name": f"Day {weekday} morning",
                            "dayofweek": str(weekday),
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        }
                    )
                    for weekday in range(5)
                ],
            }
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Repriced",
                "requires_allocation": False,
                "leave_validation_type": "no_validation",
                "create_calendar_meeting": True,
                "company_id": cls.company.id,
            }
        )

    def _employee_with_an_approved_future_leave(self):
        employee = self.env["hr.employee"].create(
            {
                "name": "Rescheduled",
                "company_id": self.company.id,
                "resource_calendar_id": self.full_time.id,
            }
        )
        day = date.today() + timedelta(days=40)
        while day.weekday() > 4:
            day += timedelta(days=1)
        leave = (
            self.env["hr.leave"]
            .with_context(leave_skip_date_check=True)
            .create(
                {
                    "employee_id": employee.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": day,
                    "request_date_to": day,
                }
            )
        )
        self.assertEqual(leave.state, "validate")
        self.assertEqual(leave.number_of_hours, 8)
        return employee, leave

    def _bookings(self, leave):
        return self.env["resource.schedule.exception"].search(
            [("holiday_id", "=", leave.id)]
        )

    def test_the_leave_is_repriced_against_the_new_schedule(self):
        employee, leave = self._employee_with_an_approved_future_leave()
        employee.write({"resource_calendar_id": self.mornings.id})
        leave.invalidate_recordset()
        self.assertEqual(
            leave.resource_calendar_id,
            self.mornings,
            "the request kept the schedule the employee no longer works, so "
            "its duration was still priced against it",
        )
        self.assertEqual(leave.number_of_hours, 4)

    def test_it_is_booked_once_not_twice(self):
        employee, leave = self._employee_with_an_approved_future_leave()
        self.assertEqual(len(self._bookings(leave)), 1)
        employee.write({"resource_calendar_id": self.mornings.id})
        self.assertEqual(
            len(self._bookings(leave)),
            1,
            "re-applying an already approved leave must replace its booking, "
            "not add a second one the working-time engine subtracts again",
        )
        self.assertEqual(len(leave.meeting_id), 1)
        self.assertTrue(leave.meeting_id.active)
        events = (
            self.env["calendar.event"]
            .with_context(active_test=False)
            .search([("res_id", "=", leave.id), ("res_model", "=", "hr.leave")])
        )
        self.assertEqual(
            events.filtered("active"),
            leave.meeting_id,
            "the superseded meeting is archived rather than left in the "
            "employee's calendar beside its replacement; it stays in the "
            "database as history, which is what cancelling a leave does too",
        )

    def test_a_caller_can_still_ask_for_no_resync(self):
        employee, leave = self._employee_with_an_approved_future_leave()
        employee.with_context(no_leave_resource_calendar_update=True).write(
            {"resource_calendar_id": self.mornings.id}
        )
        leave.invalidate_recordset()
        self.assertEqual(
            leave.resource_calendar_id,
            self.full_time,
            "the escape hatch the guard exists for still works",
        )


@tagged("post_install", "-at_install")
class TestFlexibleDurationOverAPublicHoliday(TestHrHolidaysCommon):
    """A public holiday inside a request costs nobody a day, on either kind of
    schedule."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixed = cls.env["resource.calendar"].create(
            {"name": "Fixed for holidays", "tz": "UTC", "company_id": cls.company.id}
        )
        cls.flexible = cls.env["resource.calendar"].create(
            {
                "name": "Flexible for holidays",
                "tz": "UTC",
                "company_id": cls.company.id,
                "flexible_hours": True,
                "hours_per_day": 8,
                "full_time_required_hours": 40,
            }
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Halves Over A Holiday",
                "requires_allocation": False,
                "request_unit": "half_day",
                "leave_validation_type": "hr",
                "company_id": cls.company.id,
            }
        )
        cls.env["resource.schedule.exception"].create(
            {
                "name": "A public holiday",
                "resource_id": False,
                "calendar_id": False,
                "company_id": cls.company.id,
                "date_from": "2026-03-03 00:00:00",
                "date_to": "2026-03-03 23:59:59",
            }
        )

    def _duration(self, calendar):
        employee = self.env["hr.employee"].create(
            {
                "name": f"On {calendar.name}",
                "company_id": self.company.id,
                "resource_calendar_id": calendar.id,
            }
        )
        leave = (
            self.env["hr.leave"]
            .with_context(leave_skip_date_check=True)
            .new(
                {
                    "employee_id": employee.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": date(2026, 3, 2),
                    "request_date_to": date(2026, 3, 4),
                    "request_date_from_period": "pm",
                    "request_date_to_period": "am",
                }
            )
        )
        return leave.number_of_days, leave.number_of_hours

    def test_the_holiday_is_not_charged_on_either_schedule(self):
        """Half of Monday, all of Tuesday, half of Wednesday -- with Tuesday a
        public holiday, that is one day, not two."""
        self.assertEqual(
            self._duration(self.flexible),
            self._duration(self.fixed),
            "a resource with no timetable prices the request from its own "
            "shape, and a day nobody works is not part of that shape",
        )
        self.assertEqual(self._duration(self.flexible), (1.0, 8.0))


@tagged("post_install", "-at_install")
class TestLeaveResourceCalendar(TestHrHolidaysCommon):
    """`_compute_resource_calendar_id` used to re-derive the employee's working
    schedule after `_get_calendars` had already answered, from a second
    `_read_group` over `hr.version` filtered on **version validity** dates while
    the rest of the module -- `_is_in_contract`, `_get_overlapping_contracts` --
    reads **contract** dates, and it took `[:1]` of an id-ordered recordset.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_full = cls.env["resource.calendar"].create(
            {"name": "Full 40h", "tz": "UTC", "hours_per_day": 8}
        )
        cls.calendar_half = cls.env["resource.calendar"].create(
            {"name": "Half 20h", "tz": "UTC", "hours_per_day": 4}
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Calendar probe",
                "requires_allocation": False,
            }
        )

    def test_the_calendar_is_the_one_in_force_when_the_leave_starts(self):
        employee = self.env["hr.employee"].create(
            {
                "name": "Two versions, no contract",
                "date_version": "2024-02-01",
                "resource_calendar_id": self.calendar_half.id,
            }
        )
        employee.create_version(
            {
                "date_version": "2024-01-01",
                "resource_calendar_id": self.calendar_full.id,
            }
        )
        leave = self.env["hr.leave"].create(
            {
                "name": "spans the version boundary",
                "employee_id": employee.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": "2024-01-30",
                "request_date_to": "2024-02-02",
            }
        )
        self.assertFalse(
            leave._get_overlapping_contracts(),
            "neither version carries a contract, so nothing constrains the "
            "leave to a single schedule and the compute is on its own here",
        )
        self.assertEqual(
            employee._get_calendars("2024-01-30").get(employee.id),
            self.calendar_full,
            "the version covering 30 January is the full-time one",
        )
        self.assertEqual(
            leave.resource_calendar_id,
            self.calendar_full,
            "the later version was created first, so an id-ordered [:1] used "
            "to hand the leave a schedule that does not begin until two days "
            "after it starts",
        )


@tagged("post_install", "-at_install")
class TestBalanceSearchOperators(TestHrHolidaysCommon):
    """`_search_balance` answers `not in` itself rather than leaving the ORM to
    negate its `in` answer.

    The two are not the same when `always_matches` is passed. A type needing no
    allocation has no balance, so it matches any condition on one -- including a
    negated condition. Answered through the negated inverse it was excluded from
    every one of them.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unlimited = cls.env["hr.leave.type"].create(
            {"name": "No allocation needed", "requires_allocation": False}
        )
        cls.limited = cls.env["hr.leave.type"].create(
            {"name": "Allocation needed", "requires_allocation": True}
        )
        cls.both = cls.unlimited | cls.limited

    def _search(self, operator, value):
        return self.env["hr.leave.type"].search(
            [("virtual_remaining_leaves", operator, value), ("id", "in", self.both.ids)]
        )

    def test_a_type_needing_no_allocation_matches_a_negated_balance_too(self):
        for operator, value in (("!=", 5.0), ("not in", [5.0])):
            with self.subTest(operator=operator):
                self.assertIn(
                    self.unlimited,
                    self._search(operator, value),
                    "a type with no balance to compare matches any condition on "
                    "one, and negating the positive answer dropped it instead",
                )

    def test_a_type_needing_no_allocation_still_matches_a_positive_balance(self):
        for operator, value in (("=", 5.0), ("in", [5.0]), (">", 0.0)):
            with self.subTest(operator=operator):
                self.assertIn(self.unlimited, self._search(operator, value))
