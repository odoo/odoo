import datetime
from datetime import date

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from psycopg import IntegrityError

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install", "accruals")
class TestAccrualAllocations(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": True,
                "allocation_validation_type": "hr",
            }
        )
        cls.leave_type_hour = cls.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": True,
                "allocation_validation_type": "hr",
                "request_unit": "hour",
            }
        )
        accrual_plan1_levels_fields = {
            "added_value_type": "day",
            "frequency": "monthly",
            "accrual_validity": True,
            "accrual_validity_count": 3,
            "accrual_validity_type": "month",
            "action_with_unused_accruals": "all",
        }
        accrual_plan1_levels = [
            Command.create(
                {
                    **accrual_plan1_levels_fields,
                    "milestone_date": "creation",
                    "added_value": 1,
                }
            ),
            Command.create(
                {
                    **accrual_plan1_levels_fields,
                    "milestone_date": "after",
                    "start_count": 13,
                    "start_type": "month",
                    "added_value": 2,
                }
            ),
        ]
        cls.accrual_plan_start1 = cls.env["hr.leave.accrual.plan"].create(
            {
                "name": "Accrual Plan 1 start",
                "is_based_on_worked_time": False,
                "accrued_gain_time": "start",
                "carryover_date": "allocation",
                "can_be_carryover": True,
                "level_ids": accrual_plan1_levels,
            }
        )
        cls.accrual_plan_end1 = cls.env["hr.leave.accrual.plan"].create(
            {
                "name": "Accrual Plan 1 end",
                "is_based_on_worked_time": False,
                "accrued_gain_time": "end",
                "carryover_date": "allocation",
                "can_be_carryover": True,
                "level_ids": accrual_plan1_levels,
            }
        )
        cls.leave_type_day = cls.env["hr.leave.type"].create(
            {
                "name": "Test Leave Type Days",
                "requires_allocation": "yes",
                "allocation_validation_type": "no_validation",
                "request_unit": "day",
            }
        )

    def setAllocationCreateDate(self, allocation_id, date):
        self.env.cr.execute(
            """
                       UPDATE
                       hr_leave_allocation
                       SET create_date = '%s'
                       WHERE id = %s
                       """
            % (date, allocation_id)
        )

    def assert_allocation_and_balance(
        self, allocation, expected_allocation_value, expected_balance_value, msg
    ):
        unit = allocation.accrual_plan_id.added_value_type
        allocation_value = (
            allocation.number_of_hours_display
            if unit == "hour"
            else allocation.number_of_days
        )

        leave_type_data = allocation.holiday_status_id.get_allocation_data(
            self.employee_emp
        )
        remaining_leaves = leave_type_data[self.employee_emp][0][1]["remaining_leaves"]

        self.assertAlmostEqual(
            allocation_value, expected_allocation_value, places=1, msg=msg
        )
        self.assertAlmostEqual(
            remaining_leaves, expected_balance_value, places=1, msg=msg
        )

    def test_consistency_between_cap_accrued_time_and_maximum_leave(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 1,
                                "start_type": "day",
                                "added_value": 1,
                                "added_value_type": "day",
                                "frequency": "hourly",
                                "action_with_unused_accruals": "all",
                                "cap_accrued_time": True,
                                "maximum_leave": 10000,
                            },
                        )
                    ],
                }
            )
        )
        level = accrual_plan.level_ids
        level.maximum_leave = 10
        self.assertEqual(accrual_plan.level_ids.maximum_leave, 10)

        with self.assertRaises(UserError):
            level.maximum_leave = 0

        level.cap_accrued_time = False
        self.assertEqual(accrual_plan.level_ids.maximum_leave, 0)

    def test_accrual_unlink(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                }
            )
        )

        allocation = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hrmanager_id)
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual allocation for employee",
                    "accrual_plan_id": accrual_plan.id,
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                }
            )
        )

        with self.assertRaises(ValidationError):
            accrual_plan.unlink()

        allocation.unlink()
        accrual_plan.unlink()

    def test_frequency_hourly_calendar(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "added_value_type": "day",
                                    "frequency": "hourly",
                                    "action_with_unused_accruals": "all",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            self.assertFalse(
                allocation.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation.number_of_days, 0, "There should be no days allocated yet."
            )
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                self.assertEqual(
                    allocation.number_of_days, 8, "There should be 8 day allocated."
                )
                self.assertEqual(
                    allocation.nextcall,
                    nextcall,
                    "The next call date of the cron should be in 2 days.",
                )
                allocation._update_accrual()
                self.assertEqual(
                    allocation.number_of_days,
                    8,
                    "There should be only 8 day allocated.",
                )

    def test_frequency_hourly_worked_hours(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "is_based_on_worked_time": True,
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "added_value_type": "day",
                                    "frequency": "hourly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            self.assertFalse(
                allocation.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation.number_of_days, 0, "There should be no days allocated yet."
            )
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

            leave_type = self.env["hr.leave.type"].create(
                {
                    "name": "Paid Time Off",
                    "requires_allocation": False,
                    "responsible_ids": [(4, self.user_hrmanager_id)],
                    "request_unit": "half_day",
                }
            )
            leave = self.env["hr.leave"].create(
                {
                    "name": "leave",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": "2017-12-06 08:00:00",
                    "request_date_to": "2017-12-06 17:00:00",
                    "request_date_from_period": "am",
                    "request_date_to_period": "am",
                }
            )
            leave.action_approve()

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                self.assertEqual(
                    allocation.number_of_days, 4, "There should be 4 day allocated."
                )
                self.assertEqual(
                    allocation.nextcall,
                    nextcall,
                    "The next call date of the cron should be in 2 days.",
                )
                allocation._update_accrual()
                self.assertEqual(
                    allocation.number_of_days,
                    4,
                    "There should be only 4 day allocated.",
                )

    def test_frequency_daily(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "added_value_type": "day",
                                    "frequency": "daily",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            self.assertFalse(
                allocation.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation.number_of_days, 0, "There should be no days allocated yet."
            )
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                self.assertEqual(
                    allocation.number_of_days, 1, "There should be 1 day allocated."
                )
                self.assertEqual(
                    allocation.nextcall,
                    nextcall,
                    "The next call date of the cron should be in 2 days.",
                )
                allocation._update_accrual()
                self.assertEqual(
                    allocation.number_of_days,
                    1,
                    "There should be only 1 day allocated.",
                )

    def test_frequency_weekly(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "weekly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2021-09-03",
                    }
                )
            )
            with freeze_time(datetime.date.today() + relativedelta(days=2)):
                allocation.action_approve()
                self.assertFalse(
                    allocation.nextcall,
                    "There should be no nextcall set on the allocation.",
                )
                self.assertEqual(
                    allocation.number_of_days,
                    0,
                    "There should be no days allocated yet.",
                )
                allocation._update_accrual()
                nextWeek = allocation.date_from + relativedelta(days=1, weekday=0)
                self.assertEqual(
                    allocation.number_of_days,
                    0,
                    "There should be no days allocated yet. The accrual starts tomorrow.",
                )

            with freeze_time(nextWeek):
                allocation._update_accrual()
                nextWeek = datetime.date.today() + relativedelta(days=1, weekday=0)
                self.assertAlmostEqual(
                    allocation.number_of_days,
                    0.2857,
                    4,
                    "There should be 0.2857 day allocated.",
                )
                self.assertEqual(
                    allocation.nextcall,
                    nextWeek,
                    "The next call date of the cron should be in 2 weeks",
                )

            with freeze_time(nextWeek):
                allocation._update_accrual()
                nextWeek = datetime.date.today() + relativedelta(days=1, weekday=0)
                self.assertAlmostEqual(
                    allocation.number_of_days,
                    1.2857,
                    4,
                    "There should be 1.2857 day allocated.",
                )
                self.assertEqual(
                    allocation.nextcall,
                    nextWeek,
                    "The next call date of the cron should be in 2 weeks",
                )

    def test_frequency_bimonthly(self):
        with freeze_time("2021-09-01"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "bimonthly",
                                    "repeat_day": "1",
                                    "repeat_second_day": "15",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2021-09-03",
                    }
                )
            )
            self.setAllocationCreateDate(allocation.id, "2021-09-01 00:00:00")
            allocation.action_approve()
            self.assertFalse(
                allocation.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation.number_of_days, 0, "There should be no days allocated yet."
            )
            allocation._update_accrual()
            next_date = datetime.date(2021, 9, 15)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

        with freeze_time(next_date):
            next_date = datetime.date(2021, 10, 1)
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                0.7857,
                4,
                "There should be 0.7857 day allocated.",
            )
            self.assertEqual(
                allocation.nextcall,
                next_date,
                "The next call date of the cron should be October 1st",
            )

        with freeze_time(next_date):
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                1.7857,
                4,
                "There should be 1.7857 day allocated.",
            )

    def test_frequency_monthly(self):
        with freeze_time("2021-09-01"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "monthly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2021-08-31",
                    }
                )
            )
            self.setAllocationCreateDate(allocation.id, "2021-09-01 00:00:00")
            allocation.action_approve()
            self.assertFalse(
                allocation.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation.number_of_days, 0, "There should be no days allocated yet."
            )
            allocation._update_accrual()
            next_date = datetime.date(2021, 10, 1)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

        with freeze_time(next_date):
            next_date = datetime.date(2021, 11, 1)
            allocation._update_accrual()
            self.assertEqual(
                allocation.number_of_days, 1, "There should be 1 day allocated."
            )
            self.assertEqual(
                allocation.nextcall,
                next_date,
                "The next call date of the cron should be November 1st",
            )

    def test_frequency_biyearly(self):
        with freeze_time("2021-09-01"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "biyearly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            self.setAllocationCreateDate(allocation.id, "2021-09-01 00:00:00")
            allocation.action_approve()
            self.assertFalse(
                allocation.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation.number_of_days, 0, "There should be no days allocated yet."
            )
            allocation._update_accrual()
            next_date = datetime.date(2022, 1, 1)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

        with freeze_time(next_date):
            next_date = datetime.date(2022, 7, 1)
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                0.6576,
                4,
                "There should be 0.6576 day allocated.",
            )
            self.assertEqual(
                allocation.nextcall,
                next_date,
                "The next call date of the cron should be July 1st",
            )

        with freeze_time(next_date):
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                1.6576,
                4,
                "There should be 1.6576 day allocated.",
            )

    def test_frequency_yearly(self):
        with freeze_time("2021-09-01"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "yearly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            self.setAllocationCreateDate(allocation.id, "2021-09-01 00:00:00")
            allocation.action_approve()
            self.assertFalse(
                allocation.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation.number_of_days, 0, "There should be no days allocated yet."
            )
            allocation._update_accrual()
            next_date = datetime.date(2022, 1, 1)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

        with freeze_time(next_date):
            next_date = datetime.date(2023, 1, 1)
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                0.3315,
                4,
                "There should be 0.3315 day allocated.",
            )
            self.assertEqual(
                allocation.nextcall,
                next_date,
                "The next call date of the cron should be January 1st 2023",
            )

        with freeze_time(next_date):
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                1.3315,
                4,
                "There should be 1.3315 day allocated.",
            )

    def test_check_gain(self):
        with freeze_time("2021-08-30"):
            attendances = []
            for index in range(5):
                attendances.append(
                    (
                        0,
                        0,
                        {
                            "name": "%s_%d" % ("40 Hours", index),
                            "hour_from": 8,
                            "hour_to": 12,
                            "dayofweek": str(index),
                            "day_period": "morning",
                        },
                    )
                )
                attendances.append(
                    (
                        0,
                        0,
                        {
                            "name": "%s_%d" % ("40 Hours", index),
                            "hour_from": 12,
                            "hour_to": 13,
                            "dayofweek": str(index),
                            "day_period": "lunch",
                        },
                    )
                )
                attendances.append(
                    (
                        0,
                        0,
                        {
                            "name": "%s_%d" % ("40 Hours", index),
                            "hour_from": 13,
                            "hour_to": 17,
                            "dayofweek": str(index),
                            "day_period": "afternoon",
                        },
                    )
                )
            calendar_emp = self.env["resource.calendar"].create(
                {
                    "name": "40 Hours",
                    "tz": self.employee_emp.tz,
                    "attendance_ids": attendances,
                }
            )
            self.employee_emp.resource_calendar_id = calendar_emp.id

            accrual_plan_not_based_on_worked_time = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 5,
                                    "frequency": "weekly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            accrual_plan_based_on_worked_time = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "is_based_on_worked_time": True,
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 5,
                                    "frequency": "weekly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 10000,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation_not_worked_time = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan_not_based_on_worked_time.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "state": "confirm",
                    }
                )
            )
            allocation_worked_time = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan_based_on_worked_time.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "state": "confirm",
                    }
                )
            )
            (allocation_not_worked_time | allocation_worked_time).action_approve()
            self.setAllocationCreateDate(
                allocation_not_worked_time.id, "2021-08-01 00:00:00"
            )
            self.setAllocationCreateDate(
                allocation_worked_time.id, "2021-08-01 00:00:00"
            )
            leave_type = self.env["hr.leave.type"].create(
                {
                    "name": "Paid Time Off",
                    "requires_allocation": False,
                    "responsible_ids": [Command.link(self.user_hrmanager_id)],
                }
            )
            leave = self.env["hr.leave"].create(
                {
                    "name": "leave",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": "2021-09-02",
                    "request_date_to": "2021-09-02",
                }
            )
            leave.action_approve()
            self.assertFalse(
                allocation_not_worked_time.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertFalse(
                allocation_worked_time.nextcall,
                "There should be no nextcall set on the allocation.",
            )
            self.assertEqual(
                allocation_not_worked_time.number_of_days,
                0,
                "There should be no days allocated yet.",
            )
            self.assertEqual(
                allocation_worked_time.number_of_days,
                0,
                "There should be no days allocated yet.",
            )

        next_date = datetime.date(2021, 9, 6)
        with freeze_time(next_date):
            self.env["hr.leave.allocation"]._update_accrual()
            self.assertAlmostEqual(
                allocation_not_worked_time.number_of_days,
                4.2857,
                4,
                "There should be 4.2857 days allocated.",
            )
            self.assertAlmostEqual(
                allocation_worked_time.number_of_days,
                3,
                4,
                "There should be 3 days allocated.",
            )
            self.assertEqual(
                allocation_not_worked_time.nextcall,
                datetime.date(2021, 9, 13),
                "The next call date of the cron should be the September 13th",
            )
            self.assertEqual(
                allocation_worked_time.nextcall,
                datetime.date(2021, 9, 13),
                "The next call date of the cron should be the September 13th",
            )

        with freeze_time(next_date + relativedelta(days=7)):
            next_date = datetime.date(2021, 9, 20)
            self.env["hr.leave.allocation"]._update_accrual()
            self.assertAlmostEqual(
                allocation_not_worked_time.number_of_days,
                9.2857,
                4,
                "There should be 9.2857 days allocated.",
            )
            self.assertEqual(
                allocation_not_worked_time.nextcall,
                next_date,
                "The next call date of the cron should be September 20th",
            )
            self.assertAlmostEqual(
                allocation_worked_time.number_of_days,
                8,
                4,
                "There should be 8 days allocated.",
            )
            self.assertEqual(
                allocation_worked_time.nextcall,
                next_date,
                "The next call date of the cron should be September 20th",
            )

    @freeze_time("2025-09-01")
    def test_non_eligible_leaves(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "is_based_on_worked_time": True,
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "added_value": 1,
                                "added_value_type": "day",
                                "frequency": "daily",
                                "cap_accrued_time": True,
                                "maximum_leave": 10000,
                            },
                        )
                    ],
                }
            )
        )
        allocation_worked_time = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hrmanager_id)
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual allocation for employee",
                    "accrual_plan_id": accrual_plan.id,
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                }
            )
        )
        allocation_worked_time.action_approve()
        self.assertEqual(
            allocation_worked_time.number_of_days,
            0,
            "There should be no days allocated yet.",
        )

        with freeze_time("2025-09-13"):
            allocation_worked_time._update_accrual()
            self.assertEqual(
                allocation_worked_time.number_of_days,
                10,
                "There should be 10 days allocated.",
            )

        timeoff_type = self.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": False,
                "eligible_for_accrual_rate": False,
            }
        )
        timeoff = self.env["hr.leave"].create(
            {
                "name": "Paid Time Off",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": timeoff_type.id,
                "request_date_from": "2025-09-16",
                "request_date_to": "2025-09-18",
            }
        )
        timeoff.action_approve()

        with freeze_time("2025-09-20"):
            allocation_worked_time._update_accrual()
            self.assertEqual(
                allocation_worked_time.number_of_days,
                12,
                "There should be 12 days allocated.",
            )

    @freeze_time("2025-09-01")
    def test_eligible_leaves(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "is_based_on_worked_time": True,
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "added_value": 1,
                                "added_value_type": "day",
                                "frequency": "daily",
                                "cap_accrued_time": True,
                                "maximum_leave": 10000,
                            },
                        )
                    ],
                }
            )
        )
        allocation_worked_time = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hrmanager_id)
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual allocation for employee",
                    "accrual_plan_id": accrual_plan.id,
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                }
            )
        )
        allocation_worked_time.action_approve()
        self.assertEqual(
            allocation_worked_time.number_of_days,
            0,
            "There should be no days allocated yet.",
        )

        with freeze_time("2025-09-13"):
            allocation_worked_time._update_accrual()
            self.assertEqual(
                allocation_worked_time.number_of_days,
                10,
                "There should be 10 days allocated.",
            )

        timeoff_eligible_type = self.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": False,
                "eligible_for_accrual_rate": True,
            }
        )
        timeoff_eligible = self.env["hr.leave"].create(
            {
                "name": "Paid Time Off",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": timeoff_eligible_type.id,
                "request_date_from": "2025-09-16",
                "request_date_to": "2025-09-18",
            }
        )
        timeoff_eligible.action_approve()

        with freeze_time("2025-09-20"):
            allocation_worked_time._update_accrual()
            self.assertEqual(
                allocation_worked_time.number_of_days,
                15,
                "There should be 15 days allocated.",
            )

    @freeze_time("2025-09-01")
    def test_worked_leaves(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "is_based_on_worked_time": True,
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "added_value": 1,
                                "added_value_type": "day",
                                "frequency": "daily",
                                "cap_accrued_time": True,
                                "maximum_leave": 10000,
                            },
                        )
                    ],
                }
            )
        )
        allocation_worked_time = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hrmanager_id)
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual allocation for employee",
                    "accrual_plan_id": accrual_plan.id,
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                }
            )
        )
        allocation_worked_time.action_approve()
        self.assertEqual(
            allocation_worked_time.number_of_days,
            0,
            "There should be no days allocated yet.",
        )

        with freeze_time("2025-09-13"):
            allocation_worked_time._update_accrual()
            self.assertEqual(
                allocation_worked_time.number_of_days,
                10,
                "There should be 10 days allocated.",
            )

        remote_work_type = self.env["hr.leave.type"].create(
            {
                "name": "Remote Work",
                "time_type_id": self.env.ref("resource.time_type_work").id,
                "requires_allocation": False,
            }
        )
        remote_work = self.env["hr.leave"].create(
            {
                "name": "Remote Work",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": remote_work_type.id,
                "request_date_from": "2025-09-16",
                "request_date_to": "2025-09-18",
            }
        )
        remote_work.action_approve()

        with freeze_time("2025-09-20"):
            allocation_worked_time._update_accrual()
            self.assertEqual(
                allocation_worked_time.number_of_days,
                15,
                "There should be 15 days allocated.",
            )

    def test_check_max_value(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "daily",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 1,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                allocation._update_accrual()
                self.assertEqual(
                    allocation.number_of_days,
                    1,
                    "There should be only 1 day allocated.",
                )

            with freeze_time(nextcall):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                allocation._update_accrual()
                self.assertEqual(
                    allocation.number_of_days,
                    1,
                    "There should be only 1 day allocated.",
                )

    def test_check_max_value_hours(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "hour",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "daily",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 4,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            allocation._update_accrual()
            tomorrow = datetime.date.today() + relativedelta(days=2)
            self.assertEqual(
                allocation.number_of_days,
                0,
                "There should be no days allocated yet. The accrual starts tomorrow.",
            )

            with freeze_time(tomorrow):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=10)
                allocation._update_accrual()
                self.assertEqual(
                    allocation.number_of_days,
                    0.125,
                    "There should be only 0.125 days allocated.",
                )

            with freeze_time(nextcall):
                allocation._update_accrual()
                nextcall = datetime.date.today() + relativedelta(days=1)
                allocation._update_accrual()
                self.assertEqual(
                    allocation.number_of_days,
                    0.5,
                    "There should be only 0.5 days allocated.",
                )

    def test_accrual_hours_with_max_carryover(self):
        with freeze_time("2024-10-10"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual plan - hours and max postpone",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "hour",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "repeat_day": "31",
                                    "frequency": "monthly",
                                    "action_with_unused_accruals": "all",
                                    "carryover_options": "limited",
                                    "postpone_max_days": 4,
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "date_from": datetime.date(2025, 1, 1),
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 0)

            hours_per_day = self.employee_emp.resource_calendar_id.hours_per_day
            allocation_data = self.leave_type.get_allocation_data(
                self.employee_emp, "2025-12-02"
            )[self.employee_emp][0][1]
            self.assertAlmostEqual(
                allocation_data["remaining_leaves"],
                11 / hours_per_day,
                1,
                "11 hours accrued.",
            )

            allocation_data = self.leave_type.get_allocation_data(
                self.employee_emp, "2026-02-02"
            )[self.employee_emp][0][1]
            self.assertAlmostEqual(
                allocation_data["remaining_leaves"],
                5 / hours_per_day,
                1,
                "5 hours accrued.",
            )

    def test_accrual_transition_immediately(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "transition_mode": "immediately",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "weekly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 1,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "milestone_date": "after",
                                    "start_count": 10,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "weekly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 1,
                                    "action_with_unused_accruals": "all",
                                },
                            ),
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            next_date = datetime.date.today() + relativedelta(days=11)
            second_level = self.env["hr.leave.accrual.level"].search(
                [("accrual_plan_id", "=", accrual_plan.id), ("start_count", "=", 10)]
            )
            self.assertEqual(
                allocation._get_current_accrual_plan_level_id(next_date)[0],
                second_level,
                "The second level should be selected",
            )

    def test_accrual_transition_after_period(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "transition_mode": "end_of_accrual",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "weekly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 1,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "milestone_date": "after",
                                    "start_count": 10,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "weekly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 1,
                                    "action_with_unused_accruals": "all",
                                },
                            ),
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            next_date = datetime.date.today() + relativedelta(days=11)
            second_level = self.env["hr.leave.accrual.level"].search(
                [("accrual_plan_id", "=", accrual_plan.id), ("start_count", "=", 10)]
            )
            self.assertEqual(
                allocation._get_current_accrual_plan_level_id(next_date)[0],
                second_level,
                "The second level should be selected",
            )

    def test_unused_accrual_lost(self):
        with freeze_time("2021-12-15"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "daily",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 20,
                                    "action_with_unused_accruals": "lost",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 10,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        accrual_cron = (
            self.env["ir.cron"]
            .sudo()
            .env.ref("hr_holidays.hr_leave_allocation_cron_accrual")
        )
        accrual_cron.lastcall = datetime.date(2021, 12, 15)
        with freeze_time("2022-01-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.number_of_days,
                1,
                "The number of days should reset and 1 day will be accrued on 01/01/2022.",
            )

    def test_unused_accrual_postponed(self):
        with freeze_time("2021-12-15"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "daily",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 25,
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 10,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        accrual_cron = (
            self.env["ir.cron"]
            .sudo()
            .env.ref("hr_holidays.hr_leave_allocation_cron_accrual")
        )
        accrual_cron.lastcall = datetime.date(2021, 12, 15)
        with freeze_time("2022-01-01"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            25,
            "The maximum number of days should be reached and kept.",
        )

    def test_unused_accrual_postponed_2(self):
        with freeze_time("2021-01-01"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "creation",
                                    "start_type": "day",
                                    "added_value": 2,
                                    "frequency": "yearly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 100,
                                    "action_with_unused_accruals": "all",
                                    "carryover_options": "limited",
                                    "postpone_max_days": 10,
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        accrual_cron = (
            self.env["ir.cron"]
            .sudo()
            .env.ref("hr_holidays.hr_leave_allocation_cron_accrual")
        )
        accrual_cron.lastcall = datetime.date(2021, 1, 1)
        with freeze_time("2023-01-26"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            4,
            "The maximum number of days should be reached and kept.",
        )

    def test_unused_accrual_postponed_limit(self):
        with freeze_time("2021-12-15"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "accrued_gain_time": "start",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "frequency": "daily",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 25,
                                    "action_with_unused_accruals": "all",
                                    "carryover_options": "limited",
                                    "postpone_max_days": 15,
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 10,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        accrual_cron = (
            self.env["ir.cron"]
            .sudo()
            .env.ref("hr_holidays.hr_leave_allocation_cron_accrual")
        )
        accrual_cron.lastcall = datetime.date(2021, 12, 15)
        with freeze_time("2022-01-01"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            16,
            "15 days carryover. 1 day is accrued for the new accrual period. The total is 16 days.",
        )

    def test_unused_accrual_postponed_limit_2(self):
        with freeze_time("2021-01-01"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "creation",
                                    "start_type": "day",
                                    "added_value": 15,
                                    "frequency": "yearly",
                                    "cap_accrued_time": True,
                                    "maximum_leave": 100,
                                    "action_with_unused_accruals": "all",
                                    "carryover_options": "limited",
                                    "postpone_max_days": 7,
                                },
                            )
                        ],
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        accrual_cron = (
            self.env["ir.cron"]
            .sudo()
            .env.ref("hr_holidays.hr_leave_allocation_cron_accrual")
        )
        accrual_cron.lastcall = datetime.date(2021, 1, 1)
        with freeze_time("2023-01-26"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            22,
            "7 days carryover from the previous accrual period. 15 days are accrued for the new accrual period. The total is 22 days.",
        )

    def test_accrual_skipped_period(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 15,
                                "frequency": "biyearly",
                                "cap_accrued_time": True,
                                "maximum_leave": 100,
                                "action_with_unused_accruals": "all",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 4,
                                "start_type": "month",
                                "added_value": 10,
                                "frequency": "biyearly",
                                "cap_accrued_time": True,
                                "maximum_leave": 500,
                                "action_with_unused_accruals": "all",
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2020-08-16"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Allocation - Test",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": datetime.date(2020, 8, 16),
                    }
                )
            )
            allocation.action_approve()
        with freeze_time("2022-01-10"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days, 30.82, 2, "Invalid number of days"
        )

    def test_three_levels_accrual(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 2,
                                "start_type": "month",
                                "added_value": 3,
                                "frequency": "monthly",
                                "cap_accrued_time": True,
                                "maximum_leave": 3,
                                "action_with_unused_accruals": "all",
                                "repeat_day": "31",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 3,
                                "start_type": "month",
                                "added_value": 6,
                                "frequency": "monthly",
                                "cap_accrued_time": True,
                                "maximum_leave": 6,
                                "action_with_unused_accruals": "all",
                                "repeat_day": "31",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 4,
                                "start_type": "month",
                                "added_value": 1,
                                "frequency": "monthly",
                                "cap_accrued_time": True,
                                "maximum_leave": 100,
                                "action_with_unused_accruals": "all",
                                "repeat_day": "31",
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2022-01-31"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Allocation - Test",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": datetime.date(2022, 1, 31),
                    }
                )
            )
            allocation.action_approve()
        with freeze_time("2022-07-20"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 7, 2)

    def test_accrual_lost_previous_days(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "cap_accrued_time": True,
                                "maximum_leave": 12,
                                "action_with_unused_accruals": "lost",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 1,
                                "start_type": "year",
                                "added_value": 1,
                                "frequency": "monthly",
                                "cap_accrued_time": True,
                                "maximum_leave": 12,
                                "action_with_unused_accruals": "lost",
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2021-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Allocation - Test",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": datetime.date(2021, 1, 1),
                    }
                )
            )
            allocation.action_approve()
        with freeze_time("2022-04-04"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 4, "Invalid number of days")

    def test_accrual_lost_first_january(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "accrued_gain_time": "start",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 3,
                                "frequency": "yearly",
                                "cap_accrued_time": True,
                                "maximum_leave": 12,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2019-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Allocation - Test",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": datetime.date(2019, 1, 1),
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2022-04-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days, 3, 2, "Invalid number of days"
        )

    def test_accrual_maximum_leaves(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 1,
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                                "cap_accrued_time": True,
                                "maximum_leave": 5,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2021-09-03"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2021-09-03",
                    }
                )
            )

        with freeze_time("2021-10-03"):
            allocation.action_approve()
            allocation._update_accrual()

            self.assertEqual(
                allocation.number_of_days, 5, "Should accrue maximum 5 days"
            )

    def test_accrual_maximum_leaves_no_limit(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 1,
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2021-09-03"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2021-09-03",
                    }
                )
            )

        with freeze_time("2021-10-03"):
            allocation.action_approve()
            allocation._update_accrual()

            self.assertEqual(
                allocation.number_of_days, 29, "No limits for accrued days"
            )

    def test_accrual_leaves_taken_maximum(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "weekly",
                                "repeat_weekday": "MON",
                                "cap_accrued_time": True,
                                "maximum_leave": 5,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2022-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2022-01-01",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2022-03-02"):
            allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 5, "Maximum of 5 days accrued")

        leave = self.env["hr.leave"].create(
            {
                "name": "leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": "2022-03-07",
                "request_date_to": "2022-03-11",
            }
        )
        leave.action_approve()

        with freeze_time("2022-06-01"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days, 10, "Should accrue 5 additional days"
        )

    def test_accrual_leaves_taken_maximum_hours(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "hour",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "weekly",
                                "repeat_weekday": "MON",
                                "cap_accrued_time": True,
                                "maximum_leave": 10,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time(datetime.date(2022, 1, 1)):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type_hour.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2022-01-01",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time(datetime.date(2022, 4, 1)):
            allocation._update_accrual()

        self.assertEqual(
            allocation.number_of_days,
            10 / self.hours_per_day,
            "Maximum of 10 hours accrued",
        )

        leave = self.env["hr.leave"].create(
            {
                "name": "leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": self.leave_type_hour.id,
                "request_date_from": "2022-03-07",
                "request_date_to": "2022-03-07",
            }
        )
        leave.action_approve()

        with freeze_time(datetime.date(2022, 6, 1)):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            18 / self.hours_per_day,
            "Should accrue 8 additional hours",
        )

    @mute_logger("odoo.db")
    def test_yearly_cap_constraint(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "accrued_gain_time": "end",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                                "repeat_weekday": "MON",
                                "cap_accrued_time": True,
                                "maximum_leave": 5,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with self.assertRaises(IntegrityError):
            accrual_plan.level_ids[0].write(
                {
                    "cap_accrued_time_yearly": True,
                    "maximum_leave_yearly": 0,
                }
            )
        accrual_plan.level_ids[0].write(
            {
                "cap_accrued_time_yearly": True,
                "maximum_leave_yearly": 1,
            }
        )
        accrual_plan.level_ids[0].write(
            {
                "cap_accrued_time_yearly": False,
                "maximum_leave_yearly": 0,
            }
        )
        self.env.cr.precommit.run()
        self.env.flush_all()

    def test_yearly_cap(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Hour Time Off",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "leave_validation_type": "no_validation",
                "request_unit": "hour",
            }
        )
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "accrued_gain_time": "end",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "hour",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 0.06,
                                "frequency": "hourly",
                                "repeat_weekday": "MON",
                                "cap_accrued_time": True,
                                "maximum_leave": 180,
                                "cap_accrued_time_yearly": True,
                                "maximum_leave_yearly": 120,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )

        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type.id,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "number_of_days": 0,
                    }
                )
            )

        with freeze_time("2024-12-20"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 120, 120, "The yearly cap should be reached."
            )
            leave = self.env["hr.leave"].create(
                {
                    "name": "Leave for employee",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": datetime.date(2024, 12, 19),
                    "request_date_to": datetime.date(2024, 12, 19),
                    "request_hour_from": "10",
                    "request_hour_to": "12",
                }
            )
            self.assertEqual(leave.number_of_hours, 2)
            self.assertEqual(allocation.leaves_taken, 2)
            self.assert_allocation_and_balance(
                allocation, 120, 118, "The 2 hours should be deduced from the balance"
            )

        with freeze_time("2024-12-31"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation,
                120,
                118,
                "The amount shouldn't exceed the yearly amount as all days days have already been accrued.",
            )

        with freeze_time("2025-01-06"):
            allocation._update_accrual()
            self.assertAlmostEqual(allocation.number_of_hours_display, 121.44)

        with freeze_time("2025-07-03"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 182, 180, "The global cap should be reached."
            )
            leave = self.env["hr.leave"].create(
                {
                    "name": "Leave for employee",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": datetime.date(2025, 6, 2),
                    "request_date_to": datetime.date(2025, 6, 11),
                }
            )
            self.assertEqual(leave.number_of_hours, 64)
            self.assertEqual(allocation.leaves_taken, 66)
            self.assert_allocation_and_balance(
                allocation,
                182,
                116,
                "The leave hours should be deduced from the balance.",
            )

        with freeze_time("2025-12-25"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 240, 174, "The total yearly amount should be reached."
            )

        with freeze_time("2025-12-31"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation,
                240,
                174,
                "Nothing more should have been accrued since the yearly cap was already reached.",
            )

    def test_accrual_period_start(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "accrued_gain_time": "end",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "weekly",
                                "repeat_weekday": "MON",
                                "cap_accrued_time": True,
                                "maximum_leave": 5,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-04-24"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2023-04-24",
                    }
                )
            )
            allocation.action_approve()

            allocation._update_accrual()

        self.assertEqual(
            allocation.number_of_days,
            0,
            "Should accrue 0 days, because the period is not done yet.",
        )

        accrual_plan.accrued_gain_time = "start"
        with freeze_time("2023-04-24"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2023-04-24",
                    }
                )
            )
            allocation.action_approve()

            allocation._update_accrual()

        self.assertEqual(
            allocation.number_of_days,
            1,
            "Should accrue 1 day, at the start of the period.",
        )

    def test_accrual_period_start_multiple_runs(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "accrued_gain_time": "start",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1.5,
                                "frequency": "monthly",
                                "repeat_day": "13",
                                "cap_accrued_time": True,
                                "maximum_leave": 15,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-04-13"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2023-04-13",
                    }
                )
            )
            allocation.action_approve()
            allocation._update_accrual()

        self.assertAlmostEqual(allocation.number_of_days, 1.5, 2)

        with freeze_time("2023-09-13"):
            allocation._update_accrual()

        self.assertAlmostEqual(allocation.number_of_days, 9, 2)

    def test_accrual_period_start_level_transfer(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "accrued_gain_time": "start",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "weekly",
                                "repeat_weekday": "WED",
                                "cap_accrued_time": True,
                                "maximum_leave": 10,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 3,
                                "start_type": "month",
                                "added_value": 2,
                                "frequency": "weekly",
                                "repeat_weekday": "WED",
                                "cap_accrued_time": True,
                                "maximum_leave": 5,
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2023-04-26"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2023-04-26",
                    }
                )
            )
            allocation.action_approve()
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            1,
            "Should accrue 1 day, at the start of the period.",
        )

        with freeze_time("2023-07-05"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            10,
            "Should accrue 10 days, days received, but not over limit.",
        )

        with freeze_time("2023-08-02"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            5,
            "Should accrue 5 days, after level transfer 10 are cut to 5",
        )

    def test_accrual_carryover_at_allocation(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "accrued_gain_time": "start",
                    "can_be_carryover": True,
                    "carryover_date": "allocation",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "repeat_day": "27",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-04-26"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2023-04-26",
                    }
                )
            )
            allocation.action_approve()
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days,
            0.03,
            2,
            "Should accrue 0.03 days, accrued_gain_time == start.",
        )

        with freeze_time("2023-04-27"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days,
            1.03,
            2,
            "Should accrue 1 day, days are added on 27th.",
        )

        with freeze_time("2023-12-27"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days, 9.03, 2, "Should accrue 9 day, after 8 months."
        )

        with freeze_time("2024-04-26"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days,
            0.0,
            2,
            "Allocations not lost on 1st of January, but on allocation date.",
        )

        with freeze_time("2024-04-27"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days, 1, "Allocations lost, then 1 accrued."
        )

    def test_accrual_carryover_at_other(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "accrued_gain_time": "start",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "20",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "monthly",
                                "repeat_day": "11",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 69,
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-04-20"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": "2023-04-20",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-04-20"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            69,
            "Carryover at other date, level's maximum leave is 69.",
        )

    def test_accrual_carrover_other_period_end_multi_level(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "accrued_gain_time": "end",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "5",
                    "carryover_month": "6",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 5,
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "repeat_day": "9",
                                "cap_accrued_time": True,
                                "maximum_leave": 15,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 13,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 9,
                                "start_type": "month",
                                "added_value": 2,
                                "frequency": "biyearly",
                                "repeat_day": "17",
                                "repeat_month": "2",
                                "repeat_second_day": "29",
                                "repeat_second_month": "10",
                                "cap_accrued_time": True,
                                "maximum_leave": 10,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 20,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 17,
                                "start_type": "month",
                                "added_value": 12,
                                "frequency": "yearly",
                                "repeat_month": "7",
                                "repeat_day": "15",
                                "cap_accrued_time": True,
                                "maximum_leave": 21,
                                "action_with_unused_accruals": "lost",
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2023-04-04"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 9,
                        "allocation_type": "accrual",
                        "date_from": "2023-04-04",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2026-08-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 12)

    def test_accrual_creation_on_anterior_date(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Weekly accrual",
                    "can_be_carryover": True,
                    "carryover_date": "allocation",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "weekly",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-09-01"):
            accrual_allocation = self.env["hr.leave.allocation"].new(
                {
                    "name": "Employee allocation",
                    "holiday_status_id": self.leave_type.id,
                    "date_from": "2023-01-01",
                    "employee_id": self.employee_emp.id,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                }
            )
            accrual_allocation._onchange_date_from()
            accrual_allocation.action_approve()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 34.0, places=0)
            self.assertFalse(
                accrual_allocation.lastcall == accrual_allocation.date_from
            )
            accrual_allocation._update_accrual()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 34.0, places=0)

    def test_future_accural_time(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Test Leave Type",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "request_unit": "hour",
            }
        )
        with freeze_time("2023-12-31"):
            accrual_plan = self.env["hr.leave.accrual.plan"].create(
                {
                    "name": "Accrual Plan For Test",
                    "is_based_on_worked_time": False,
                    "accrued_gain_time": "end",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "after",
                                "start_count": 1,
                                "start_type": "day",
                                "added_value": 1,
                                "added_value_type": "hour",
                                "frequency": "monthly",
                                "cap_accrued_time": True,
                                "maximum_leave": 100,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
            allocation = self.env["hr.leave.allocation"].create(
                {
                    "name": "Accrual allocation for employee",
                    "accrual_plan_id": accrual_plan.id,
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 0.125,
                    "allocation_type": "accrual",
                }
            )
            allocation.action_approve()
            allocation_data = leave_type.get_allocation_data(
                self.employee_emp, datetime.date(2024, 2, 1)
            )
            self.assertEqual(
                allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"], 2
            )

    def test_added_type_during_onchange(self):
        accrual_plan = self.env["hr.leave.accrual.plan"].create(
            {
                "name": "Accrual Plan For Test",
                "is_based_on_worked_time": False,
                "accrued_gain_time": "end",
                "can_be_carryover": True,
                "carryover_date": "year_start",
                "level_ids": [
                    (
                        0,
                        0,
                        {
                            "milestone_date": "after",
                            "start_count": 1,
                            "start_type": "day",
                            "added_value": 4,
                            "added_value_type": "hour",
                            "frequency": "monthly",
                            "cap_accrued_time": True,
                            "maximum_leave": 100,
                            "action_with_unused_accruals": "all",
                        },
                    )
                ],
            }
        )
        form = Form(accrual_plan)
        with form.level_ids.new() as level:
            self.assertEqual(level.added_value_type, "hour")

    def test_accrual_immediate_cron_run(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Weekly accrual",
                    "can_be_carryover": True,
                    "carryover_date": "allocation",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-09-01"):
            accrual_allocation = self.env["hr.leave.allocation"].new(
                {
                    "name": "Employee allocation",
                    "holiday_status_id": self.leave_type.id,
                    "date_from": "2023-08-01",
                    "employee_id": self.employee_emp.id,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                }
            )
            accrual_allocation._onchange_date_from()
            accrual_allocation.action_approve()
            self.assertEqual(
                accrual_allocation.number_of_days,
                31.0,
                "The allocation should have given 31 days",
            )
            accrual_allocation._update_accrual()
            self.assertEqual(
                accrual_allocation.number_of_days,
                31.0,
                "the amount shouldn't have changed after running the cron",
            )

    def test_accrual_creation_for_history(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Monthly accrual",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "repeat_day": "31",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2024-03-02"):
            accrual_allocation = self.env["hr.leave.allocation"].new(
                {
                    "name": "History allocation",
                    "holiday_status_id": self.leave_type.id,
                    "date_from": "2024-03-01",
                    "employee_id": self.employee_emp.id,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                }
            )
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 0, places=0)

            accrual_allocation.write({"date_from": "2022-01-01"})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 2, places=0)

            accrual_allocation.write({"date_to": "2022-12-31"})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 12, places=0)

    def test_accrual_with_report_creation_for_history(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Monthly accrual",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "repeat_day": "31",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 5,
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2024-03-02"):
            accrual_allocation = self.env["hr.leave.allocation"].new(
                {
                    "name": "History allocation",
                    "holiday_status_id": self.leave_type.id,
                    "date_from": "2024-03-01",
                    "employee_id": self.employee_emp.id,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                }
            )
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 0, places=0)

            accrual_allocation.write({"date_from": "2022-01-01"})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 7, places=0)

            accrual_allocation.write({"date_to": "2022-12-31"})
            accrual_allocation._onchange_date_from()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 12, places=0)

    def test_accrual_period_start_past_start_date(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Monthly accrual",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "start",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "repeat_day": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2024-03-01"):
            with Form(
                self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
            ) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = "2024-01-01"
                f.employee_id = self.employee_emp
                f.holiday_status_id = self.leave_type
                f.name = "Employee Allocation"

            accrual_allocation = f.record
            accrual_allocation.action_approve()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 3.0, places=0)

        with freeze_time("2024-04-01"):
            accrual_allocation._update_accrual()
            self.assertAlmostEqual(accrual_allocation.number_of_days, 4.0, places=0)

    def test_cancel_invalid_leaves_with_regular_and_accrual_allocations(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Monthly accrual",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "start",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "repeat_day": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        allocations = self.env["hr.leave.allocation"].create(
            [
                {
                    "name": "Regular allocation",
                    "allocation_type": "regular",
                    "date_from": "2024-05-01",
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": self.employee_emp.id,
                    "number_of_days": 2,
                },
                {
                    "name": "Accrual allocation",
                    "allocation_type": "accrual",
                    "date_from": "2024-05-01",
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": self.employee_emp.id,
                    "accrual_plan_id": accrual_plan.id,
                    "number_of_days": 3,
                },
            ]
        )
        allocations.action_approve()
        leave = self.env["hr.leave"].create(
            {
                "name": "Leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": "2024-05-13",
                "request_date_to": "2024-05-17",
            }
        )
        leave.action_approve()
        with freeze_time("2024-05-06"):
            self.env["hr.leave"]._cancel_invalid_leaves()
        self.assertEqual(leave.state, "validate", "Leave must not be canceled")

    def test_accrual_leaves_cancel_cron(self):
        leave_type_no_negative = self.env["hr.leave.type"].create(
            {
                "name": "Test Accrual - No negative",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "leave_validation_type": "no_validation",
                "allows_negative": False,
            }
        )
        leave_type_negative = self.env["hr.leave.type"].create(
            {
                "name": "Test Accrual - Negative",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
                "leave_validation_type": "no_validation",
                "allows_negative": True,
                "max_allowed_negative": 1,
            }
        )
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Monthly accrual",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "repeat_day": "31",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 5,
                            },
                        )
                    ],
                }
            )
        )

        with freeze_time("2024-01-01"):
            self.env["hr.leave.allocation"].create(
                [
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type_no_negative.id,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "number_of_days": 1,
                    },
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type_negative.id,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "number_of_days": 1,
                    },
                ]
            )

            excess_leave = self.env["hr.leave"].create(
                [
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type_no_negative.id,
                        "request_date_from": "2024-01-05",
                        "request_date_to": "2024-01-05",
                    }
                ]
            )
            allowed_negative_leave = self.env["hr.leave"].create(
                [
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type_negative.id,
                        "request_date_from": "2024-01-12",
                        "request_date_to": "2024-01-12",
                    }
                ]
            )

            self.env["hr.leave"].create(
                [
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type_no_negative.id,
                        "request_date_from": "2024-01-04",
                        "request_date_to": "2024-01-04",
                    },
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type_negative.id,
                        "request_date_from": "2024-01-11",
                        "request_date_to": "2024-01-11",
                    },
                ]
            )
            self.env.flush_all()

            self.env["hr.leave"]._cancel_invalid_leaves()

            self.assertEqual(excess_leave.state, "cancel")
            self.assertEqual(allowed_negative_leave.state, "validate")

            self.env["hr.leave"].create(
                [
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type_negative.id,
                        "request_date_from": "2024-01-10",
                        "request_date_to": "2024-01-10",
                    }
                ]
            )

            self.env["hr.leave"]._cancel_invalid_leaves()

            self.assertEqual(allowed_negative_leave.state, "cancel")

    def test_check_lastcall_change_regular_to_accrual(self):
        with freeze_time("2017-12-05"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual Plan For Test",
                    }
                )
            )
            allocation = (
                self.env["hr.leave.allocation"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 10,
                        "allocation_type": "regular",
                    }
                )
            )
            allocation.action_approve()

            self.assertEqual(allocation.lastcall, False)

            allocation.action_refuse()
            allocation.write(
                {
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                }
            )

            self.assertEqual(allocation.lastcall, datetime.date(2017, 12, 5))

    def test_accrual_allocation_data_persists(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Test Leave Type",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
            }
        )
        accrual_plan = self.env["hr.leave.accrual.plan"].create(
            {
                "name": "Accrual Plan For Test",
                "accrued_gain_time": "start",
                "can_be_carryover": True,
                "carryover_date": "year_start",
                "level_ids": [
                    (
                        0,
                        0,
                        {
                            "milestone_date": "after",
                            "start_count": 1,
                            "start_type": "day",
                            "added_value": 1,
                            "added_value_type": "day",
                            "frequency": "daily",
                            "cap_accrued_time": True,
                            "maximum_leave": 10,
                            "action_with_unused_accruals": "all",
                        },
                    )
                ],
            }
        )

        def get_remaining_leaves(*args):
            return leave_type.get_allocation_data(
                self.employee_emp, datetime.date(*args)
            )[self.employee_emp][0][1]["remaining_leaves"]

        with freeze_time("2024-03-01"):
            with Form(
                self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
            ) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.employee_id = self.employee_emp
                f.holiday_status_id = leave_type
                f.date_from = "2024-02-01"
                f.name = "Accrual allocation for employee"

            first_result = get_remaining_leaves(2024, 2, 21)
            self.assertEqual(
                get_remaining_leaves(2024, 2, 21),
                first_result,
                "Function return result should persist",
            )

    def test_future_accural_time_with_leaves_taken_in_the_past(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Test Leave Type",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
            }
        )
        accrual_plan = self.env["hr.leave.accrual.plan"].create(
            {
                "name": "Accrual Plan For Test",
                "accrued_gain_time": "start",
                "can_be_carryover": True,
                "carryover_date": "year_start",
                "level_ids": [
                    (
                        0,
                        0,
                        {
                            "milestone_date": "after",
                            "start_count": 1,
                            "start_type": "day",
                            "added_value": 1,
                            "added_value_type": "day",
                            "frequency": "daily",
                            "cap_accrued_time": True,
                            "maximum_leave": 10,
                            "action_with_unused_accruals": "all",
                        },
                    )
                ],
            }
        )

        def get_remaining_leaves(*args):
            return leave_type.get_allocation_data(
                self.employee_emp, datetime.date(*args)
            )[self.employee_emp][0][1]["remaining_leaves"]

        with freeze_time("2024-03-01"):
            with Form(
                self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
            ) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.employee_id = self.employee_emp
                f.holiday_status_id = leave_type
                f.date_from = "2024-02-01"
                f.name = "Accrual allocation for employee"

            self.assertEqual(
                get_remaining_leaves(2024, 3, 1),
                10,
                "The cap is reached, no more leaves should be accrued",
            )

            leave = self.env["hr.leave"].create(
                {
                    "name": "leave",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": "2024-02-26",
                    "request_date_to": "2024-03-01",
                }
            )
            leave.action_approve()
            self.assertEqual(
                get_remaining_leaves(2024, 3, 1),
                5,
                "5 day should be deduced from the allocation",
            )
            self.assertEqual(
                get_remaining_leaves(2024, 3, 3),
                7,
                "2 days should be added to the accrual allocation",
            )
            self.assertEqual(
                get_remaining_leaves(2024, 3, 10),
                10,
                "Accrual allocation should be capped at 10",
            )

            leave = self.env["hr.leave"].create(
                {
                    "name": "leave",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": "2024-03-04",
                    "request_date_to": "2024-03-08",
                }
            )
            leave.action_approve()
            self.assertEqual(
                get_remaining_leaves(2024, 3, 4),
                3,
                "5 days should be deduced from the allocation and a new day should be accrued",
            )
            self.assertEqual(
                get_remaining_leaves(2024, 3, 11),
                10,
                "Accrual allocation should be capped at 10",
            )

    @freeze_time("2024-01-01")
    def test_validate_leaves_with_more_days_than_allocation(self):
        allocation = (
            self.env["hr.leave.allocation"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual allocation for employee",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "number_of_days": 1,
                    "allocation_type": "regular",
                }
            )
        )

        allocation.action_approve()
        with self.assertRaises(ValidationError):
            self.env["hr.leave"].create(
                [
                    {
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "request_date_from": "2024-01-09",
                        "request_date_to": "2024-01-12",
                    }
                ]
            )

        leave = self.env["hr.leave"].create(
            [
                {
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2024-01-09 08:00:00",
                    "request_date_to": "2024-01-09 17:00:00",
                }
            ]
        )

        leave.action_approve()
        leave.action_refuse()
        leave.write(
            {
                "request_date_from": "2024-01-09",
                "request_date_to": "2024-01-12",
            }
        )

        with self.assertRaises(ValidationError):
            leave.action_approve()

    def test_compute_allocation_days_after_adding_employee(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Monthly accrual",
                    "is_based_on_worked_time": True,
                    "transition_mode": "immediately",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 1,
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                                "repeat_day": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                            },
                        ),
                    ],
                }
            )
        )

        with freeze_time("2024-08-19"):
            attendances = []
            for index in range(3):
                attendances.extend(
                    [
                        (
                            0,
                            0,
                            {
                                "name": "%s_%d" % ("20 Hours", index),
                                "hour_from": 8,
                                "hour_to": 10,
                                "dayofweek": str(index),
                                "day_period": "morning",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": "%s_%d" % ("20 Hours", index),
                                "hour_from": 10,
                                "hour_to": 11,
                                "dayofweek": str(index),
                                "day_period": "lunch",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": "%s_%d" % ("20 Hours", index),
                                "hour_from": 11,
                                "hour_to": 13,
                                "dayofweek": str(index),
                                "day_period": "afternoon",
                            },
                        ),
                    ]
                )
            calendar_emp = self.env["resource.calendar"].create(
                {
                    "name": "20 Hours",
                    "tz": self.employee_hrmanager.tz,
                    "attendance_ids": attendances,
                }
            )
            self.employee_hrmanager.resource_calendar_id = calendar_emp.id

            with Form(
                self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
            ) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = "2024-08-07"
                f.holiday_status_id = self.leave_type
                f.employee_id = self.employee_emp
                f.name = "Employee Allocation"

            accrual_allocation = f.record
            allocation_days = accrual_allocation.number_of_days
            self.assertEqual(accrual_allocation.number_of_days, 7.0)

            with Form(accrual_allocation) as accForm:
                accForm.employee_id = self.employee_hrmanager

            updated_allocation = accForm.record

            self.assertNotEqual(updated_allocation.number_of_days, allocation_days)
            self.assertEqual(updated_allocation.number_of_days, 3.0)

    def test_no_days_accrued_on_carryover_date(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "7",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value": 10,
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "date_from": datetime.date(2024, 1, 1),
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "10 days should be accrued")

        with freeze_time("2025-07-01"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            10,
            "No Days should be accrued on the carryover date",
        )

        with freeze_time("2026-01-01"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            20,
            "10 additional days should be accrued on January 1st. The total number of accrued days should be 20",
        )

    def test_matching_accrual_and_carryover_dates(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value": 10,
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "frequency": "yearly",
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "date_from": datetime.date(2024, 1, 1),
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10, "10 days are accrued")

        with freeze_time("2026-01-01"):
            allocation._update_accrual()
        self.assertEqual(
            allocation.number_of_days,
            10,
            "All previous days are lost. 10 new days are added.",
        )

    def test_matching_carryover_and_level_transition_dates(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "7",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value": 12,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "action_with_unused_accruals": "lost",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "added_value": 14,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "milestone_date": "after",
                                "start_count": 18,
                                "start_type": "month",
                                "action_with_unused_accruals": "lost",
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "date_from": datetime.date(2024, 1, 1),
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 12, "12 days are accrued")

        with freeze_time("2025-07-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days,
            6,
            1,
            "All previous days are lost. 6 new days are added.",
        )
        with freeze_time("2026-01-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(
            allocation.number_of_days,
            13,
            1,
            "7 days are accrued. Total days = 6 + 7 = 13.",
        )

    def test_accrual_plan_with_multiple_levels(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "accrued_gain_time": "start",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "6",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value": 1,
                                "added_value_type": "day",
                                "frequency": "monthly",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "action_with_unused_accruals": "lost",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "added_value": 1,
                                "added_value_type": "day",
                                "frequency": "monthly",
                                "milestone_date": "after",
                                "start_count": 20,
                                "start_type": "month",
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 5,
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "date_from": datetime.date(2024, 1, 1),
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-05-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 5)

        with freeze_time("2024-06-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 1)

        with freeze_time("2024-08-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 3)

        with freeze_time("2024-09-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 4)

        with freeze_time("2024-12-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 7)

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 8)

    def test_accrual_plan_with_multiple_levels_2(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "accrued_gain_time": "start",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "6",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value": 10,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "action_with_unused_accruals": "lost",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "added_value": 12,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "milestone_date": "after",
                                "start_count": 32,
                                "start_type": "month",
                                "action_with_unused_accruals": "all",
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "date_from": datetime.date(2024, 1, 1),
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-01-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10)

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 20)

        with freeze_time("2025-06-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 0)

        with freeze_time("2026-01-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 10)

        with freeze_time("2026-06-01"):
            allocation._update_accrual()
        self.assertEqual(allocation.number_of_days, 0)

        with freeze_time("2026-09-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 10.7, 1)

        with freeze_time("2027-01-01"):
            allocation._update_accrual()
        self.assertAlmostEqual(allocation.number_of_days, 22.67, 2)

    def test_carried_over_days_expiry_date_computation(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "biyearly",
                                "repeat_month": "1",
                                "repeat_day": "1",
                                "repeat_second_month": "7",
                                "repeat_second_day": "1",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 5,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 17,
                                "start_type": "month",
                                "added_value": 20,
                                "frequency": "biyearly",
                                "repeat_month": "1",
                                "repeat_day": "1",
                                "repeat_second_month": "7",
                                "repeat_second_day": "1",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 2,
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2023-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-04-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2024, 9, 1)
            )

    def test_carried_over_days_expiry_date_computation_2(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 2,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 2,
                                "start_type": "year",
                                "added_value": 20,
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 3,
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2023-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-04-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2024, 6, 1)
            )

        with freeze_time("2025-04-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2025, 7, 1)
            )

    def test_carried_over_days_expiry_date_computation_3(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "5",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 2,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "after",
                                "start_count": 29,
                                "start_type": "month",
                                "added_value": 20,
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 3,
                            },
                        ),
                    ],
                }
            )
        )
        with freeze_time("2023-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-05-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1)
            )

        with freeze_time("2025-05-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2025, 7, 1)
            )

        with freeze_time("2026-01-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2026, 8, 1)
            )

    def test_carried_over_days_expiry_date_computation_4(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "5",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 2,
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-05-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1)
            )

        accrual_plan.carryover_month = "7"
        with freeze_time("2025-01-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1)
            )

        with freeze_time("2025-07-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1)
            )

    def test_carried_over_days_expiry_date_computation_5(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "5",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "monthly",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 2,
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-05-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1)
            )

        with freeze_time("2024-06-01"):
            accrual_plan.carryover_month = "7"
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2024, 7, 1)
            )

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1)
            )

        with freeze_time("2025-07-01"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.carried_over_days_expiration_date, datetime.date(2025, 9, 1)
            )

    def test_carried_over_days_expiry(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "20",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 5,
                                "accrual_validity": True,
                                "accrual_validity_type": "day",
                                "accrual_validity_count": 20,
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 10)
        with freeze_time("2025-04-20"):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 5)
        with freeze_time("2025-05-10"):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 0)

    def test_time_off_using_expiring_carried_over_days(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "biyearly",
                                "repeat_month": "1",
                                "repeat_day": "1",
                                "repeat_second_month": "7",
                                "repeat_second_day": "1",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 5,
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2024-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-07-01"):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 10)
        with freeze_time("2025-01-01"):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 20)
        with freeze_time("2025-04-01"):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 20)
        with freeze_time("2025-07-01"):
            allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, 30)

        leave = self.env["hr.leave"].create(
            {
                "name": "leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": "2025-07-02",
                "request_date_to": "2025-07-04",
            }
        )
        leave.action_approve()

        with freeze_time("2025-09-01"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 13, 10, "The employee balance should be 10 days."
            )

    def test_time_off_balance_computation(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "day",
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 10,
                                "frequency": "yearly",
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 5,
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 5,
                            },
                        )
                    ],
                }
            )
        )
        with freeze_time("2023-01-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()

        with freeze_time("2024-01-01"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 10, 10, "The employee was accrued 10 days"
            )

        leave = self.env["hr.leave"].create(
            {
                "name": "leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": "2024-03-25",
                "request_date_to": "2024-03-26",
            }
        )
        leave.action_approve()

        with freeze_time("2024-04-01"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 7, 5, "Only 5 days will carry over"
            )

        leave = self.env["hr.leave"].create(
            {
                "name": "leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": "2024-04-02",
                "request_date_to": "2024-04-02",
            }
        )
        leave.action_approve()

        with freeze_time("2024-09-01"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 3, 0, "The 5 carried over days should expire"
            )

        with freeze_time("2025-01-01"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 13, 10, "The employee was accrued 10 days"
            )

        leave = self.env["hr.leave"].create(
            {
                "name": "leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": "2025-01-08",
                "request_date_to": "2025-01-10",
            }
        )
        leave.action_approve()

        with freeze_time("2025-04-01"):
            allocation._update_accrual()
            self.assert_allocation_and_balance(
                allocation, 11, 5, "Only 5 days will carry over"
            )

    def test_carriedover_days_expiration_reset(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                    "can_be_carryover": True,
                    "carryover_date": "allocation",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 1,
                                "added_value_type": "day",
                                "frequency": "monthly",
                                "action_with_unused_accruals": "all",
                                "accrual_validity": True,
                                "accrual_validity_type": "month",
                                "accrual_validity_count": 1,
                            },
                        )
                    ],
                }
            )
        )

        with freeze_time("2023-08-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "date_from": "2023-08-01",
                    }
                )
            )

        with freeze_time("2024-09-25"):
            allocation._onchange_date_from()
            self.assertEqual(allocation.number_of_days, 2)

            allocation.date_from = "2023-09-01"
            allocation._onchange_date_from()
            self.assertEqual(allocation.number_of_days, 12)

            allocation.date_from = "2023-08-01"
            allocation._onchange_date_from()
            self.assertEqual(allocation.number_of_days, 2)

    def test_start_accrual_gain_time_immediately(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "1.25 days each 1st of the month",
                    "transition_mode": "immediately",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "start",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "start_type": "day",
                                "milestone_date": "creation",
                                "added_value_type": "day",
                                "added_value": 1.25,
                                "frequency": "monthly",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )

        with freeze_time("2024-09-02"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )

            allocation.action_approve()
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                1.21,
                2,
                "Days for the current month should be granted immediately",
            )

            leave = self.env["hr.leave"].create(
                {
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2024-09-13 08:00:00",
                    "request_date_to": "2024-09-13 17:00:00",
                }
            )
            leave.action_approve()
            remaining_leaves = self.leave_type.get_allocation_data(
                self.employee_emp, date(2024, 9, 14)
            )[self.employee_emp][0][1]["remaining_leaves"]
            self.assertAlmostEqual(
                remaining_leaves, 0.21, 2, "Leave should be deducted from accrued days"
            )

        with freeze_time("2024-10-01"):
            allocation._update_accrual()
            self.assertAlmostEqual(
                allocation.number_of_days,
                2.46,
                2,
                "Days for the upcoming month should be granted on the 1st",
            )

    def test_set_accrual_allocation_to_zero_from_ui(self):
        with freeze_time("2024-06-15"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "2 days on the 1st of each month",
                        "accrued_gain_time": "start",
                        "can_be_carryover": True,
                        "carryover_date": "year_start",
                        "level_ids": [
                            Command.create(
                                {
                                    "added_value_type": "day",
                                    "milestone_date": "creation",
                                    "start_type": "day",
                                    "added_value": 2,
                                    "frequency": "monthly",
                                }
                            )
                        ],
                    }
                )
            )

            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )

            with Form(allocation) as f:
                f.date_from = "2024-01-01"
                f.number_of_days_display = 0
            allocation.action_approve()

            remaining_leaves = self.leave_type.get_allocation_data(
                self.employee_emp, date(2024, 7, 15)
            )[self.employee_emp][0][1]["remaining_leaves"]
            self.assertAlmostEqual(
                remaining_leaves,
                2,
                2,
                "Only 2 days gained on 1st of July should be accrued",
            )

    def test_cache_invalidation_with_future_leaves(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "1 days every last day of the month",
                    "transition_mode": "immediately",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "start_type": "day",
                                "milestone_date": "creation",
                                "added_value_type": "day",
                                "added_value": 1,
                                "frequency": "monthly",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                                "repeat_day": "31",
                            },
                        )
                    ],
                }
            )
        )

        with freeze_time("2024-06-30"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp_id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                    }
                )
            )
            allocation.action_approve()
            allocation._update_accrual()

            leave = self.env["hr.leave"].create(
                {
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2024-09-02",
                    "request_date_to": "2024-09-03",
                }
            )
            leave.action_approve()

        with freeze_time("2024-07-31"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.number_of_days,
                1,
                "Days should be allocated even when leave is taken in the future",
            )

    def test_accrual_days_left_under_carryover_maximum(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "21 days per year, 28 days cap, 7 carryover max",
                    "transition_mode": "immediately",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "start",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "accrued_gain_time": "start",
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "added_value": 21,
                                "cap_accrued_time": True,
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "frequency": "yearly",
                                "maximum_leave": 28,
                                "postpone_max_days": 7,
                                "start_count": 0,
                                "start_type": "day",
                            },
                        )
                    ],
                }
            )
        )

        with freeze_time("2024-11-25"):
            with Form(
                self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
            ) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = "2024-01-01"
                f.employee_id = self.employee_emp
                f.holiday_status_id = self.leave_type
                f.name = "Employee Allocation"

            allocation = f.record
            allocation.action_approve()

            leave = self.env["hr.leave"].create(
                {
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2024-10-07",
                    "request_date_to": "2024-10-25",
                }
            )
            leave.action_approve()
            data = self.leave_type.get_allocation_data(
                self.employee_emp, date(2025, 1, 15)
            )
            remaining_future = data[self.employee_emp][0][1]["remaining_leaves"]
            self.assertEqual(remaining_future, 27)

    def test_accrual_unused_accrual_reset_to_lost(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "21 days per year, 28 days cap, 7 carryover max",
                    "transition_mode": "immediately",
                    "can_be_carryover": True,
                    "carryover_date": "year_start",
                    "accrued_gain_time": "start",
                }
            )
        )

        plan = (
            self.env["hr.leave.accrual.level"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "accrual_plan_id": accrual_plan.id,
                }
            )
        )

        with Form(plan) as f:
            f.added_value = 21
            f.frequency = "yearly"
            f.repeat_day = "1"
            f.cap_accrued_time = True
            f.maximum_leave = 28
            f.start_count = 0
            f.action_with_unused_accruals = "all"
            f.carryover_options = "limited"
            f.postpone_max_days = 7
            f.action_with_unused_accruals = "lost"

        with freeze_time("2024-11-25"):
            with Form(
                self.env["hr.leave.allocation"].with_user(self.user_hrmanager)
            ) as f:
                f.allocation_type = "accrual"
                f.accrual_plan_id = accrual_plan
                f.date_from = "2024-01-01"
                f.employee_id = self.employee_emp
                f.holiday_status_id = self.leave_type
                f.name = "Employee Allocation"

            allocation = f.record
            allocation.action_approve()

            leave = self.env["hr.leave"].create(
                {
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2024-10-07",
                    "request_date_to": "2024-10-25",
                }
            )
            leave.action_approve()
            data = self.leave_type.get_allocation_data(
                self.employee_emp, date(2025, 1, 15)
            )
            remaining_future = data[self.employee_emp][0][1]["remaining_leaves"]
            self.assertEqual(remaining_future, 21)

    def test_accrual_allocation_without_working_hours(self):
        with freeze_time("2017-12-05"):
            employee_without_calendar = self.env["hr.employee"].create(
                {
                    "name": "employee without calendar",
                    "resource_calendar_id": False,
                }
            )
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "is_based_on_worked_time": True,
                        "can_be_carryover": True,
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "milestone_date": "after",
                                    "start_count": 1,
                                    "start_type": "day",
                                    "added_value": 1,
                                    "added_value_type": "hour",
                                    "frequency": "hourly",
                                    "action_with_unused_accruals": "all",
                                },
                            )
                        ],
                    }
                )
            )
            past_date = datetime.date.today() - relativedelta(days=1)
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "accrual allocation for employee without calendar",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": employee_without_calendar.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": past_date,
                    }
                )
            )
            future_date = datetime.date.today() + relativedelta(days=1)
            allocation._process_accrual_plans(date_to=future_date)

    def test_accrual_allocation_with_virtual_future_leaves(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Test Leave Type",
                "requires_allocation": True,
                "leave_validation_type": "hr",
                "allocation_validation_type": "hr",
                "employee_requests": False,
            }
        )
        accrual_plan = self.env["hr.leave.accrual.plan"].create(
            {
                "name": "Accrual Plan with no carryover",
                "accrued_gain_time": "start",
                "can_be_carryover": True,
                "carryover_date": "year_start",
                "level_ids": [
                    Command.create(
                        {
                            "added_value": 8,
                            "added_value_type": "day",
                            "action_with_unused_accruals": "lost",
                            "frequency": "yearly",
                            "repeat_month": "1",
                            "repeat_day": "1",
                        }
                    )
                ],
            }
        )

        with freeze_time("2024-12-01"):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_user(self.user_hrmanager_id)
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation for employee",
                        "accrual_plan_id": accrual_plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": leave_type.id,
                        "date_from": "2024-12-01",
                        "number_of_days": 8,
                        "allocation_type": "accrual",
                        "nextcall": "2025-01-01",
                    }
                )
            )
            allocation.action_approve()
            leave = self.env["hr.leave"].create(
                {
                    "name": "Virtual Leave",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": "2024-12-23",
                    "request_date_to": "2024-12-24",
                }
            )
            self.assertNotEqual(
                leave.state,
                "validate",
                "The leave request should not be in the 'validate' state",
            )

        with freeze_time("2025-01-05"):
            allocation._update_accrual()
            self.assertEqual(
                allocation.number_of_days,
                8,
                "The number of days should be updated successfully",
            )

    def test_accrual_allocation_constraint_1(self):
        with self.assertRaises(ValidationError):
            self.env["hr.leave.accrual.plan"].create(
                {
                    "name": "Accrual Plan with no carryover",
                    "accrued_gain_time": "start",
                    "carryover_date": "year_start",
                    "level_ids": [
                        Command.create(
                            {
                                "added_value": 8,
                                "added_value_type": "day",
                                "action_with_unused_accruals": "lost",
                                "frequency": "bimonthly",
                                "repeat_day": "20",
                                "repeat_second_day": "3",
                            }
                        )
                    ],
                }
            )

    def test_accrual_allocation_data_with_different_units(self):
        with freeze_time("2024-01-01"):
            accrual_plan = self.env["hr.leave.accrual.plan"].create(
                {
                    "name": "Accrual Plan For Test",
                    "is_based_on_worked_time": False,
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "hour",
                                "start_count": 0,
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                            },
                        )
                    ],
                }
            )
            leave_type_day = self.env["hr.leave.type"].create(
                {
                    "name": "Test Leave Type",
                    "requires_allocation": "yes",
                    "allocation_validation_type": "no_validation",
                    "request_unit": "day",
                }
            )

            allocation = self.env["hr.leave.allocation"].create(
                {
                    "name": "Accrual allocation for employee",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type_day.id,
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "date_from": "2024-01-01",
                }
            )
            allocation.action_approve()
        with freeze_time("2024-01-09"):
            allocation._update_accrual()
            allocation_data = leave_type_day.get_allocation_data(self.employee_emp)
            self.assertEqual(
                allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"], 1
            )

    def test_accrual_allocation_data_with_different_units_half_day(self):
        with freeze_time("2024-01-01"):
            accrual_plan = self.env["hr.leave.accrual.plan"].create(
                {
                    "name": "Accrual Plan For Test",
                    "is_based_on_worked_time": False,
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "hour",
                                "start_count": 0,
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                            },
                        )
                    ],
                }
            )
            leave_type_day = self.env["hr.leave.type"].create(
                {
                    "name": "Test Leave Type",
                    "requires_allocation": "yes",
                    "allocation_validation_type": "no_validation",
                    "request_unit": "half_day",
                }
            )

            allocation = self.env["hr.leave.allocation"].create(
                {
                    "name": "Accrual allocation for employee",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type_day.id,
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "date_from": "2024-01-01",
                }
            )
            allocation.action_approve()
        with freeze_time("2024-01-09"):
            allocation._update_accrual()
            allocation_data = leave_type_day.get_allocation_data(self.employee_emp)
            self.assertEqual(
                allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"], 1
            )

    def test_accrual_allocation_data_with_different_units_and_used_days(self):
        with freeze_time("2024-01-01"):
            accrual_plan = self.env["hr.leave.accrual.plan"].create(
                {
                    "name": "Accrual Plan For Test",
                    "is_based_on_worked_time": False,
                    "accrued_gain_time": "end",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "added_value_type": "hour",
                                "start_count": 0,
                                "start_type": "day",
                                "added_value": 1,
                                "frequency": "daily",
                            },
                        )
                    ],
                }
            )
            leave_type_day = self.env["hr.leave.type"].create(
                {
                    "name": "Test Leave Type",
                    "requires_allocation": "yes",
                    "allocation_validation_type": "no_validation",
                    "request_unit": "day",
                }
            )

            allocation = self.env["hr.leave.allocation"].create(
                {
                    "name": "Accrual allocation for employee",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type_day.id,
                    "number_of_days": 0,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "date_from": "2024-01-01",
                }
            )
            allocation.action_approve()
        with freeze_time("2024-01-17"):
            allocation._update_accrual()
            leave = self.env["hr.leave"].create(
                {
                    "name": "Leave",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type_day.id,
                    "request_date_from": "2024-01-05",
                    "request_date_to": "2024-01-05",
                }
            )
            leave.action_approve()
            allocation_data = leave_type_day.get_allocation_data(self.employee_emp)
            self.assertEqual(
                allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"], 1
            )

    def _create_monthly_plan(self, day, added_value=2, **plan_values):
        level_values = plan_values.pop("level_values", {})
        return self.env["hr.leave.accrual.plan"].create(
            {
                "name": f"Monthly on the {day}",
                "accrued_gain_time": "end",
                "carryover_date": "allocation",
                **plan_values,
                "level_ids": [
                    Command.create(
                        {
                            "start_count": 0,
                            "start_type": "day",
                            "added_value": added_value,
                            "added_value_type": "day",
                            "frequency": "monthly",
                            "repeat_day": day,
                            "cap_accrued_time": False,
                            **level_values,
                        }
                    )
                ],
            }
        )

    def _accrue_draft(self, plan, date_from, today):
        with freeze_time(today):
            allocation = self.env["hr.leave.allocation"].new(
                {
                    "name": "Draft accrual",
                    "employee_id": self.employee_emp.id,
                    "allocation_type": "accrual",
                    "accrual_plan_id": plan.id,
                    "date_from": date_from,
                    "holiday_status_id": self.leave_type.id,
                }
            )
            allocation._onchange_date_from()
            return allocation.number_of_days

    def _create_approved_allocation(self, plan, date_from):
        with freeze_time(date_from):
            allocation = (
                self.env["hr.leave.allocation"]
                .with_context(tracking_disable=True)
                .create(
                    {
                        "name": "Accrual allocation",
                        "accrual_plan_id": plan.id,
                        "employee_id": self.employee_emp.id,
                        "holiday_status_id": self.leave_type.id,
                        "number_of_days": 0,
                        "allocation_type": "accrual",
                        "date_from": date_from,
                    }
                )
            )
            allocation.action_approve()
        return allocation

    def test_a_last_day_level_credits_a_whole_first_month(self):
        plan = self._create_monthly_plan("last")
        self.assertEqual(self._accrue_draft(plan, date(2025, 1, 1), "2025-01-31"), 2.0)

    def test_a_31st_level_prorates_the_day_its_first_period_started_before(self):
        # The 31st is a boundary like any other day: the period it closes runs
        # from Dec 31, which the allocation starting Jan 1 did not cover.
        plan = self._create_monthly_plan("31")
        self.assertAlmostEqual(
            self._accrue_draft(plan, date(2025, 1, 1), "2025-01-31"), 2 * 30 / 31
        )

    def test_one_period_has_one_length_whichever_month_a_start_falls_in(self):
        plan = self._create_monthly_plan("15", added_value=1)
        self.assertAlmostEqual(
            self._accrue_draft(plan, date(2024, 12, 20), "2025-01-15"), 26 / 31
        )
        self.assertAlmostEqual(
            self._accrue_draft(plan, date(2025, 1, 1), "2025-01-15"), 14 / 31
        )

    def test_a_last_day_level_is_credited_on_the_last_day_and_only_once(self):
        plan = self._create_monthly_plan("last", added_value=1)
        allocation = self._create_approved_allocation(plan, date(2025, 1, 1))
        for today, expected in (
            ("2025-01-30", 0),
            ("2025-01-31", 1),
            ("2025-01-31", 1),
            ("2025-02-01", 1),
            ("2025-02-27", 1),
            ("2025-02-28", 2),
        ):
            with freeze_time(today):
                allocation._update_accrual()
            self.assertEqual(allocation.number_of_days, expected, today)

    def test_a_last_day_credit_lands_before_the_carryover_it_precedes(self):
        plan_values = {
            "carryover_date": "year_start",
            "can_be_carryover": True,
            "level_values": {
                "action_with_unused_accruals": "all",
                "carryover_options": "limited",
                "postpone_max_days": 3,
            },
        }
        daily = self._create_approved_allocation(
            self._create_monthly_plan("last", **plan_values), date(2025, 10, 1)
        )
        caught_up = self._create_approved_allocation(
            self._create_monthly_plan("last", **plan_values), date(2025, 10, 1)
        )
        first_of_month = self._create_approved_allocation(
            self._create_monthly_plan("1", **plan_values), date(2025, 10, 1)
        )
        day = date(2025, 10, 1)
        while day <= date(2026, 1, 2):
            with freeze_time(day):
                daily._update_accrual()
            day += relativedelta(days=1)
        with freeze_time("2026-01-02"):
            caught_up._update_accrual()
            first_of_month._update_accrual()
        # October, November and December are credited on their last days, and the
        # carryover on Jan 1 keeps 3 of the 6. On the 1st, December's credit comes
        # after that carryover instead.
        self.assertEqual(daily.number_of_days, 3)
        self.assertEqual(caught_up.number_of_days, 3)
        self.assertEqual(first_of_month.number_of_days, 5)

    def test_the_last_day_and_the_next_first_day_are_not_two_dates(self):
        level_values = {
            "added_value": 1,
            "added_value_type": "day",
            "frequency": "bimonthly",
            "repeat_second_day": "last",
        }
        with self.assertRaises(ValidationError):
            self.env["hr.leave.accrual.plan"].create(
                {
                    "name": "Same boundary twice",
                    "level_ids": [Command.create({**level_values, "repeat_day": "1"})],
                }
            )
        plan = self.env["hr.leave.accrual.plan"].create(
            {
                "name": "The 15th and the last day",
                "level_ids": [Command.create({**level_values, "repeat_day": "15"})],
            }
        )
        self.assertEqual(plan.level_ids.repeat_second_day, "last")

    @freeze_time("2025-01-01")
    def test_accrual_allocation_date_in_the_future(self):
        vals = {
            "milestone_date": "after",
            "accrual_validity": True,
            "accrual_validity_count": 6,
            "accrual_validity_type": "month",
            "accrued_gain_time": "start",
            "action_with_unused_accruals": "all",
            "cap_accrued_time_yearly": False,
            "frequency": "yearly",
            "carryover_options": "limited",
            "postpone_max_days": 5,
            "repeat_weekday": "MON",
        }
        accrual_plan = self.env["hr.leave.accrual.plan"].create(
            {
                "name": "Test accrual plan",
                "is_based_on_worked_time": False,
                "accrued_gain_time": "start",
                "can_be_carryover": True,
                "level_ids": [
                    (
                        0,
                        0,
                        {
                            **vals,
                            "added_value": 20,
                            "milestone_date": "creation",
                            "start_type": "day",
                            "maximum_leave": 25,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            **vals,
                            "added_value": 21,
                            "start_count": 2,
                            "start_type": "year",
                            "maximum_leave": 26,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            **vals,
                            "added_value": 22,
                            "start_count": 4,
                            "start_type": "year",
                            "maximum_leave": 27,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            **vals,
                            "added_value": 23,
                            "start_count": 6,
                            "start_type": "year",
                            "maximum_leave": 28,
                        },
                    ),
                ],
            }
        )

        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Test Leave Type",
                "requires_allocation": "yes",
                "allocation_validation_type": "no_validation",
                "request_unit": "day",
            }
        )

        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Accrual allocation for employee",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": leave_type.id,
                "number_of_days": 20,
                "allocation_type": "accrual",
                "accrual_plan_id": accrual_plan.id,
                "date_from": "2025-01-01",
            }
        )
        allocation.action_approve()
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2026-03-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            25,
            "The carryover did not expire yet so the remaining leaves should be 25",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2026-09-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            20,
            "The carryover expired after 6 month so the remaining leaves should be 20",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2027-03-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            26,
            "The carryover did not expire yet so the remaining leaves should be 26",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2027-09-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            21,
            "The carryover expired after 6 month so the remaining leaves should be 21",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2028-03-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            26,
            "The carryover did not expire yet so the remaining leaves should be 26",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2028-09-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            21,
            "The carryover expired after 6 month so the remaining leaves should be 21",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2029-03-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            27,
            "The carryover did not expire yet so the remaining leaves should be 27",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2029-09-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            22,
            "The carryover expired after 6 month so the remaining leaves should be 22",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2030-03-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            27,
            "The carryover did not expire yet so the remaining leaves should be 27",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2030-09-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            22,
            "The carryover expired after 6 month so the remaining leaves should be 22",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2031-03-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            28,
            "The carryover did not expire yet so the remaining leaves should be 28",
        )
        allocation_data = leave_type.get_allocation_data(
            self.employee_emp, "2031-09-01"
        )
        self.assertEqual(
            allocation_data[self.employee_emp][0][1]["virtual_remaining_leaves"],
            23,
            "The carryover expired after 6 month so the remaining leaves should be 23",
        )

    def test_accrual_plan_cleared_when_switch_to_regular(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan For Test",
                }
            )
        )
        allocation = (
            self.env["hr.leave.allocation"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual allocation for employee",
                    "allocation_type": "accrual",
                    "holiday_status_id": self.leave_type.id,
                    "accrual_plan_id": accrual_plan.id,
                    "employee_id": self.employee_emp.id,
                    "number_of_days": 10,
                }
            )
        )
        self.assertEqual(
            allocation.accrual_plan_id,
            accrual_plan,
            "Accrual plan should initially be set.",
        )

        with Form(allocation) as alloc_form:
            alloc_form.allocation_type = "regular"
        self.assertFalse(
            allocation.accrual_plan_id,
            "accrual_plan_id should be cleared automatically when type becomes 'regular'.",
        )
        self.assertEqual(
            accrual_plan.employees_count,
            0,
            "Accrual plan should not have any linked employees.",
        )

    def test_accrual_plan_start_carryover_expiring_3_months(self):
        with freeze_time("2025-07-01"):
            allocation = self._create_form_test_accrual_allocation(
                self.leave_type_day,
                "2025-07-01",
                self.employee_emp,
                self.accrual_plan_start1,
            )
            allocation.action_approve()

        assertions = [
            ("2026-07-01", leaves := 13, 12),
            ("2026-09-30", leaves := leaves + 4, 12),
            ("2026-10-01", leaves := leaves + 2 - 12, 0),
            ("2026-11-01", leaves + 2, 0),
        ]

        for test_date, remaining_leaves, expiring_days in assertions:
            with freeze_time(test_date):
                allocation._update_accrual()
                self.assert_remaining_leaves_equal(
                    self.leave_type_day,
                    remaining_leaves,
                    self.employee_emp,
                    test_date,
                    digits=3,
                )
                self.assertAlmostEqual(
                    allocation.expiring_carryover_days,
                    expiring_days,
                    2,
                    msg=f"Incorrect number of expiring days for {test_date}",
                )

    def test_accrual_plan_end_carryover_expiring_3_months(self):
        with freeze_time("2025-07-01"):
            allocation = self._create_form_test_accrual_allocation(
                self.leave_type_day,
                "2025-07-01",
                self.employee_emp,
                self.accrual_plan_end1,
            )
            allocation.action_approve()

        assertions = [
            ("2026-07-01", leaves := 12, 11),
            ("2026-09-30", leaves := leaves + 3, 11),
            ("2026-10-01", leaves := leaves + 2 - 11, 0),
            ("2026-11-01", leaves + 2, 0),
        ]

        for test_date, remaining_leaves, expiring_days in assertions:
            with freeze_time(test_date):
                allocation._update_accrual()
                self.assert_remaining_leaves_equal(
                    self.leave_type_day,
                    remaining_leaves,
                    self.employee_emp,
                    test_date,
                    digits=3,
                )
                self.assertAlmostEqual(
                    allocation.expiring_carryover_days,
                    expiring_days,
                    2,
                    msg=f"Incorrect number of expiring days for {test_date}",
                )

    def test_accrual_leaves_cancel_cron_with_refused_allocation(self):
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Test Accrual",
                "requires_allocation": "yes",
                "allocation_validation_type": "no_validation",
                "leave_validation_type": "no_validation",
                "allows_negative": True,
                "max_allowed_negative": 2,
            }
        )

        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Accrual Plan",
                    "carryover_date": "year_start",
                    "accrued_gain_time": "end",
                }
            )
        )

        with freeze_time("2024-01-01"):
            allocation = self.env["hr.leave.allocation"].create(
                {
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "number_of_days": 1,
                }
            )

            leave = self.env["hr.leave"].create(
                {
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": "2024-01-05",
                    "request_date_to": "2024-01-05",
                }
            )

            allocation.action_refuse()
            self.env["hr.leave"]._cancel_invalid_leaves()
            self.assertEqual(leave.state, "cancel")
