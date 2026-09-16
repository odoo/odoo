from datetime import date

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests.common import tagged, users

from odoo.addons.base.tests.common import HttpCase
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install", "carryover_expiring_leaves")
class TestExpiringLeaves(HttpCase, TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Test",
                "requires_allocation": True,
                "allocation_validation_type": "no_validation",
            }
        )
        cls.accrual_plan_with_accrual_validity = (
            cls.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan With Accrual Validity",
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "start_count": 0,
                                "start_type": "day",
                                "added_value": 3,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": 5,
                                "accrual_validity": True,
                                "accrual_validity_count": 3,
                                "accrual_validity_type": "month",
                            },
                        )
                    ],
                }
            )
        )

    @users("enguerran")
    def test_no_carried_over_leaves(self):
        number_of_accrued_days = 10
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "31",
                    "carryover_month": "12",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": number_of_accrued_days,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )

        logged_in_emp = self.env.user.employee_id
        allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "date_from": date(date.today().year, 1, 1),
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )
        )

        target_date = date(date.today().year + 1, 12, 30)
        leave = self.env["hr.leave"].create(
            {
                "employee_id": logged_in_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": target_date + relativedelta(month=12, day=1),
                "request_date_to": target_date + relativedelta(month=12, day=7),
            }
        )

        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            allocation._get_carryover_date(target_date).strftime("%m/%d/%Y"),
            "The expiration date should match the carryover date",
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"],
            number_of_accrued_days - leave.number_of_days,
            "All the remaining days of the allocation will expire",
        )

    @users("enguerran")
    def test_carried_over_leaves_with_maximum(self):
        number_of_accrued_days = 20
        carryover_limit = 10
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "31",
                    "carryover_month": "12",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": number_of_accrued_days,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": carryover_limit,
                            },
                        )
                    ],
                }
            )
        )

        logged_in_emp = self.env.user.employee_id
        allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "date_from": date(date.today().year, 1, 1),
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )
        )

        target_date = date(date.today().year + 1, 12, 30)
        leave = self.env["hr.leave"].create(
            {
                "employee_id": logged_in_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": target_date + relativedelta(month=12, day=1),
                "request_date_to": target_date + relativedelta(month=12, day=7),
            }
        )
        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            allocation._get_carryover_date(target_date).strftime("%m/%d/%Y"),
            "The expiration date should match the carryover date",
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"],
            number_of_accrued_days - leave.number_of_days - carryover_limit,
            "All the remaining days of the allocation will expire",
        )

    @users("enguerran")
    def test_allocation_with_max_carryover_and_expiring_allocation(self):
        number_of_accrued_days = 20
        carryover_limit = 10
        accrual_plan_1 = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "31",
                    "carryover_month": "12",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": number_of_accrued_days,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                                "carryover_options": "limited",
                                "postpone_max_days": carryover_limit,
                            },
                        )
                    ],
                }
            )
        )

        accrual_plan_2 = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan With All Leaves Carried Over",
                    "can_be_carryover": True,
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": number_of_accrued_days,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "all",
                            },
                        )
                    ],
                }
            )
        )

        logged_in_emp = self.env.user.employee_id
        with freeze_time("2024-01-01"):
            allocation_with_carryover = (
                self.env["hr.leave.allocation"]
                .sudo()
                .create(
                    {
                        "date_from": "2024-01-01",
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan_1.id,
                        "holiday_status_id": self.leave_type.id,
                        "employee_id": logged_in_emp.id,
                        "number_of_days": 0,
                    }
                )
            )
            leave = self.env["hr.leave"].create(
                {
                    "employee_id": logged_in_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2025-12-01",
                    "request_date_to": "2025-12-05",
                }
            )
            self.env["hr.leave.allocation"].sudo().create(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2025-12-31",
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan_2.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )

            target_date = date(2025, 12, 30)
            allocation_data = self.leave_type.get_allocation_data(
                logged_in_emp, target_date
            )

            self.assertEqual(
                allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
                allocation_with_carryover._get_carryover_date(target_date).strftime(
                    "%m/%d/%Y"
                ),
                "The expiration date should match the carryover date",
            )

            self.assertEqual(
                allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"],
                (number_of_accrued_days - leave.number_of_days - carryover_limit)
                + number_of_accrued_days,
                "All the remaining days of the allocation will expire",
            )

    @users("enguerran")
    def test_expiring_allocation_without_carried_over_leaves(self):
        number_of_accrued_days = 10
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "31",
                    "carryover_month": "12",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": number_of_accrued_days,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )

        logged_in_emp = self.env.user.employee_id
        allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "date_from": date(date.today().year, 1, 1),
                    "date_to": date(date.today().year + 1, 12, 31),
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )
        )

        target_date = date(date.today().year + 1, 12, 30)
        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            allocation._get_carryover_date(target_date).strftime("%m/%d/%Y"),
            "The expiration date should match the carryover date",
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"],
            number_of_accrued_days,
            "All the remaining days of the allocation will expire",
        )

    @users("enguerran")
    def test_expiration_date(self):
        with freeze_time("2024-01-01"):
            accrual_plan = (
                self.env["hr.leave.accrual.plan"]
                .with_context(tracking_disable=True)
                .sudo()
                .create(
                    {
                        "name": "Test Accrual Plan",
                        "can_be_carryover": True,
                        "carryover_date": "year_start",
                        "level_ids": [
                            (
                                0,
                                0,
                                {
                                    "milestone_date": "creation",
                                    "start_type": "day",
                                    "added_value": 10,
                                    "added_value_type": "day",
                                    "frequency": "yearly",
                                    "repeat_day": "1",
                                    "repeat_month": "1",
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

            logged_in_emp = self.env.user.employee_id
            allocation = (
                self.env["hr.leave.allocation"]
                .sudo()
                .create(
                    {
                        "date_from": date(2024, 1, 1),
                        "allocation_type": "accrual",
                        "accrual_plan_id": accrual_plan.id,
                        "holiday_status_id": self.leave_type.id,
                        "employee_id": logged_in_emp.id,
                        "number_of_days": 0,
                    }
                )
            )

            target_date = date(2025, 1, 1)
            allocation_data = self.leave_type.get_allocation_data(
                allocation.employee_id, target_date
            )
            self.assertEqual(
                allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
                (target_date + relativedelta(years=1)).strftime("%m/%d/%Y"),
                "The expiration date should be the carryover date of the year that follows the target date's year",
            )

            self.assertEqual(
                allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"], 5
            )

    @users("enguerran")
    def test_expiration_date_2(self):
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "9",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": 3,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
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

        logged_in_emp = self.env.user.employee_id
        with freeze_time("2023-01-01"):
            self.env["hr.leave.allocation"].sudo().create(
                {
                    "date_from": "2023-01-01",
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )
            self.env["hr.leave.allocation"].sudo().create(
                {
                    "date_from": "2023-01-01",
                    "date_to": "2024-10-01",
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )

        with freeze_time("2024-01-01"):
            self.env["hr.leave.allocation"].with_user(
                self.user_hruser
            )._update_accrual()

        target_date = date(2024, 1, 1)
        allocation_data = self.leave_type.get_allocation_data(
            logged_in_emp, target_date
        )
        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            (target_date + relativedelta(month=10)).strftime("%m/%d/%Y"),
            "The expiration date should be the expiration date of the second allocation because no days will expire on carryover date",
        )

    @users("enguerran")
    def test_no_carried_over_leaves_for_flexible_resource(self):
        number_of_accrued_days = 10
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "31",
                    "carryover_month": "12",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": number_of_accrued_days,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )

        self.flex_40h_calendar = (
            self.env["resource.calendar"]
            .sudo()
            .create(
                {
                    "name": "Flexible 40h/week",
                    "tz": "UTC",
                    "hours_per_day": 8.0,
                    "full_time_required_hours": 80.0,
                    "flexible_hours": True,
                }
            )
        )
        logged_in_emp = self.env.user.employee_id
        logged_in_emp.resource_calendar_id = self.flex_40h_calendar

        allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "date_from": date(date.today().year, 1, 1),
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )
        )

        target_date = date(date.today().year + 1, 12, 30)
        leave = self.env["hr.leave"].create(
            {
                "employee_id": logged_in_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": target_date + relativedelta(month=12, day=1),
                "request_date_to": target_date + relativedelta(month=12, day=7),
            }
        )

        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            allocation._get_carryover_date(target_date).strftime("%m/%d/%Y"),
            "The expiration date should match the carryover date",
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"],
            number_of_accrued_days - leave.number_of_days,
            "All the remaining days of the allocation will expire",
        )

    @users("enguerran")
    def test_no_carried_over_leaves_for_fully_flexible_resource(self):
        number_of_accrued_days = 10
        accrual_plan = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "can_be_carryover": True,
                    "carryover_date": "other",
                    "carryover_day": "31",
                    "carryover_month": "12",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "milestone_date": "creation",
                                "start_type": "day",
                                "added_value": number_of_accrued_days,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
                                "cap_accrued_time": False,
                                "action_with_unused_accruals": "lost",
                            },
                        )
                    ],
                }
            )
        )

        logged_in_emp = self.env.user.employee_id
        logged_in_emp.resource_calendar_id = None

        allocation = (
            self.env["hr.leave.allocation"]
            .sudo()
            .create(
                {
                    "date_from": date(date.today().year, 1, 1),
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )
        )

        target_date = date(date.today().year + 1, 12, 30)
        leave = self.env["hr.leave"].create(
            {
                "employee_id": logged_in_emp.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": target_date + relativedelta(month=12, day=1),
                "request_date_to": target_date + relativedelta(month=12, day=7),
            }
        )

        allocation_data = self.leave_type.get_allocation_data(
            allocation.employee_id, target_date
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            allocation._get_carryover_date(target_date).strftime("%m/%d/%Y"),
            "The expiration date should match the carryover date",
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"],
            number_of_accrued_days - leave.number_of_days,
            "All the remaining days of the allocation will expire",
        )

        working_days_equivalent_needed = (
            allocation._get_carryover_date(target_date) - target_date
        ).days + 1

        self.assertEqual(
            round(allocation_data[logged_in_emp][0][1]["closest_allocation_duration"]),
            working_days_equivalent_needed,
            "The closest allocation duration should be the number of working days equivalent (24 hours/day) remaining before the allocation expires",
        )

    @users("enguerran")
    def test_carried_over_days_expiration_date(self):
        accrual_plan_without_accrual_validity = (
            self.env["hr.leave.accrual.plan"]
            .with_context(tracking_disable=True)
            .sudo()
            .create(
                {
                    "name": "Test Accrual Plan",
                    "carryover_date": "other",
                    "carryover_day": "1",
                    "carryover_month": "4",
                    "level_ids": [
                        (
                            0,
                            0,
                            {
                                "start_count": 0,
                                "start_type": "day",
                                "added_value": 3,
                                "added_value_type": "day",
                                "frequency": "yearly",
                                "repeat_day": "1",
                                "repeat_month": "1",
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

        logged_in_emp = self.env.user.employee_id
        with freeze_time("2023-01-01"):
            self.env["hr.leave.allocation"].sudo().create(
                {
                    "date_from": "2023-01-01",
                    "date_to": "2024-10-01",
                    "allocation_type": "accrual",
                    "accrual_plan_id": accrual_plan_without_accrual_validity.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )
            self.env["hr.leave.allocation"].sudo().create(
                {
                    "date_from": "2023-01-01",
                    "allocation_type": "accrual",
                    "accrual_plan_id": self.accrual_plan_with_accrual_validity.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )

        with freeze_time("2024-04-01"):
            self.env["hr.leave.allocation"].with_user(
                self.user_hruser
            )._update_accrual()

        target_date = date(2024, 4, 1)
        allocation_data = self.leave_type.get_allocation_data(
            logged_in_emp, target_date
        )
        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            (target_date + relativedelta(month=7)).strftime("%m/%d/%Y"),
            "The expiration date should be the carried over days expiration date of allocation 3",
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"], 3
        )

    @users("enguerran")
    def test_carried_over_expiration_is_read_at_the_target_date(self):
        """The projection is built for ``target_date``; every field read back
        off it must be read in that same context. ``leaves_taken`` is
        ``depends_context("default_date_from")``, so a read outside it answers
        for today instead -- and a leave between today and the target date is
        then counted as still to come, leaving the carried-over days reading
        unconsumed.
        """
        logged_in_emp = self.env.user.employee_id
        with freeze_time("2023-01-01"):
            self.env["hr.leave.allocation"].sudo().create(
                {
                    "date_from": "2023-01-01",
                    "allocation_type": "accrual",
                    "accrual_plan_id": self.accrual_plan_with_accrual_validity.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )

        with freeze_time("2024-04-01"):
            self.env["hr.leave.allocation"].with_user(
                self.user_hruser
            )._update_accrual()
            leave = self.env["hr.leave"].create(
                {
                    "name": "leave",
                    "employee_id": logged_in_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2024-04-03",
                    "request_date_to": "2024-04-04",
                }
            )
            leave.sudo().action_approve()

            target_date = date(2024, 5, 1)
            allocation_data = self.leave_type.get_allocation_data(
                logged_in_emp, target_date
            )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"],
            1,
            "the two days taken on 3-4 April are behind the 1 May target date, "
            "so only one of the three carried-over days is still to expire",
        )

    @users("enguerran")
    def test_carried_over_days_expiration_date_2(self):
        logged_in_emp = self.env.user.employee_id
        with freeze_time("2023-01-01"):
            self.env["hr.leave.allocation"].sudo().create(
                {
                    "date_from": "2023-01-01",
                    "allocation_type": "accrual",
                    "accrual_plan_id": self.accrual_plan_with_accrual_validity.id,
                    "holiday_status_id": self.leave_type.id,
                    "employee_id": logged_in_emp.id,
                    "number_of_days": 0,
                }
            )

        with freeze_time("2024-04-01"):
            self.env["hr.leave.allocation"].with_user(
                self.user_hruser
            )._update_accrual()
            leave = self.env["hr.leave"].create(
                {
                    "name": "leave",
                    "employee_id": logged_in_emp.id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2024-04-03",
                    "request_date_to": "2024-04-04",
                }
            )
            leave.sudo().action_approve()

        target_date = date(2024, 5, 1)
        allocation_data = self.leave_type.get_allocation_data(
            logged_in_emp, target_date
        )
        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_expire"],
            (target_date + relativedelta(month=7)).strftime("%m/%d/%Y"),
            "The expiration date should be the carried over days expiration date of allocation 3",
        )

        self.assertEqual(
            allocation_data[logged_in_emp][0][1]["closest_allocation_remaining"], 1
        )
