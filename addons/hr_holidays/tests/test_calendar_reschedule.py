# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install")
class TestCalendarReschedule(TestHrHolidaysCommon):
    """Covers ``can_reschedule`` and the backend behaviour the calendar drag relies on."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        WorkEntryType = cls.env["hr.work.entry.type"].with_user(cls.user_hrmanager_id)
        cls.type_no_validation = WorkEntryType.create(
            {
                "name": "Reschedule - no validation",
                "code": "RESCH_NOVAL",
                "requires_allocation": False,
                "leave_validation_type": "no_validation",
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )
        cls.type_manager = WorkEntryType.create(
            {
                "name": "Reschedule - manager validation",
                "code": "RESCH_MGR",
                "requires_allocation": False,
                "leave_validation_type": "manager",
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )
        cls.type_hours = WorkEntryType.create(
            {
                "name": "Reschedule - hourly",
                "code": "RESCH_HOUR",
                "requires_allocation": False,
                "leave_validation_type": "manager",
                "request_unit": "hour",
                "unit_of_measure": "hour",
            }
        )
        cls.type_allocated = WorkEntryType.create(
            {
                "name": "Reschedule - allocated",
                "code": "RESCH_ALLOC",
                "requires_allocation": True,
                "employee_requests": True,
                "leave_validation_type": "manager",
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )

    def _create_leave(self, work_entry_type, date_from, date_to, user=None):
        model = self.env["hr.leave"]
        if user:
            model = model.with_user(user)
        return model.create(
            {
                "name": "Reschedule test",
                "employee_id": self.employee_emp_id,
                "work_entry_type_id": work_entry_type.id,
                "request_date_from": date_from,
                "request_date_to": date_to,
            }
        )

    @freeze_time("2024-01-08")
    def test_pending_leave_is_reschedulable_by_owner(self):
        # A request still "To Approve" can be moved freely by its owner.
        leave = self._create_leave(
            self.type_manager, "2024-02-05", "2024-02-06", user=self.user_employee_id
        )
        self.assertEqual(leave.state, "confirm")
        self.assertTrue(leave.with_user(self.user_employee_id).can_reschedule)

    @freeze_time("2024-01-08")
    def test_approved_leave_not_reschedulable_without_reset_right(self):
        # Approving resets nobody but the officer may send it back to "To Approve",
        # so only a real officer (group_hr_holidays_user) can drag it.
        leave = self._create_leave(
            self.type_manager, "2024-02-05", "2024-02-06", user=self.user_employee_id
        )
        leave.with_user(self.user_responsible_id).action_approve()
        self.assertEqual(leave.state, "validate")

        # Owner: cannot reset an approved leave -> not draggable.
        self.assertFalse(leave.with_user(self.user_employee_id).can_reschedule)
        # Leave manager but not an officer: same restriction holds.
        self.assertFalse(leave.with_user(self.user_responsible_id).can_reschedule)
        # Officer: allowed the validate -> confirm transition -> draggable.
        self.assertTrue(leave.with_user(self.user_hruser_id).can_reschedule)

    @freeze_time("2024-01-08")
    def test_auto_approved_leave_moves_freely(self):
        # A no-validation request is auto-approved on create but never needs a real
        # approval. Whoever may write it can move it freely (no re-approval), here an
        # officer. The employee cannot modify their own validated leave (existing
        # ir.access rule), so it is not draggable for them: we never loosen that.
        leave = self._create_leave(
            self.type_no_validation,
            "2024-02-05",
            "2024-02-06",
            user=self.user_employee_id,
        )
        self.assertEqual(leave.state, "validate")
        self.assertEqual(leave.validation_type, "no_validation")
        self.assertTrue(leave.with_user(self.user_hruser_id).can_reschedule)
        self.assertFalse(leave.with_user(self.user_employee_id).can_reschedule)

    @freeze_time("2024-01-08")
    def test_reschedule_resets_state_to_confirm(self):
        # Rescheduling an approved leave (as an officer) sends it back to "To Approve".
        leave = self._create_leave(
            self.type_manager, "2024-02-05", "2024-02-06", user=self.user_employee_id
        )
        leave.with_user(self.user_responsible_id).action_approve()
        self.assertEqual(leave.state, "validate")

        leave.with_user(self.user_hruser_id).write(
            {
                "state": "confirm",
                "request_date_from": "2024-03-04",
                "request_date_to": "2024-03-05",
            }
        )
        self.assertEqual(leave.state, "confirm")

    @freeze_time("2024-01-08")
    def test_calendar_drag_writes_request_dates(self):
        # A drag sends the endpoints the calendar displays, request_date_hour_from/to,
        # whose end is exclusive. reschedule_from_calendar maps them back onto the
        # writable request_date_from/to, from which the leave is recomputed.
        leave = self._create_leave(
            self.type_manager, "2024-02-05", "2024-02-06", user=self.user_employee_id
        ).with_user(self.user_employee_id)
        self.assertEqual(leave.state, "confirm")

        # four weeks later: the same weekdays, so the request keeps its extent
        leave.reschedule_from_calendar(
            leave.request_date_hour_from + relativedelta(weeks=4),
            leave.request_date_hour_to + relativedelta(weeks=4),
        )
        self.assertEqual(leave.request_date_from, fields.Date.from_string("2024-03-04"))
        self.assertEqual(leave.request_date_to, fields.Date.from_string("2024-03-05"))

    @freeze_time("2024-01-08")
    def test_hourly_resize_moves_request_hours(self):
        # An hourly leave's extent lives in request_hour_from/to: a resize on the time
        # grid lands there, and date_from/to follow from the recompute.
        leave = (
            self.env["hr.leave"]
            .with_user(self.user_employee_id)
            .create(
                {
                    "name": "Hourly",
                    "employee_id": self.employee_emp_id,
                    "work_entry_type_id": self.type_hours.id,
                    "request_date_from": "2024-02-05",
                    "request_date_to": "2024-02-05",
                    "request_hour_from": 10,
                    "request_hour_to": 12,
                }
            )
        )
        self.assertEqual(leave.work_entry_type_request_unit, "hour")
        original_to = leave.date_to

        leave.reschedule_from_calendar(
            leave.request_date_hour_from,
            leave.request_date_hour_to + relativedelta(hours=2),
        )
        self.assertEqual(leave.request_hour_to, 14)
        self.assertEqual(
            leave.date_to,
            original_to + relativedelta(hours=2),
            "The dragged end is carried by request_hour_to",
        )

    @freeze_time("2024-01-08")
    def test_reschedule_beyond_allocation_is_rejected(self):
        # Increasing the duration past the available allocation must be refused.
        allocation = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hruser_id)
            .create(
                {
                    "name": "Reschedule allocation",
                    "employee_id": self.employee_emp_id,
                    "work_entry_type_id": self.type_allocated.id,
                    "number_of_days": 2,
                    "date_from": "2024-01-01",
                    "date_to": "2024-12-31",
                }
            )
        )
        allocation.action_approve()

        leave = self._create_leave(
            self.type_allocated, "2024-02-05", "2024-02-06", user=self.user_employee_id
        )
        leave.with_user(self.user_responsible_id).action_approve()
        self.assertEqual(leave.state, "validate")

        # Mon 2024-02-05 -> Thu 2024-02-08 is four working days, the allocation covers two.
        with self.assertRaises(ValidationError):
            leave.with_user(self.user_hruser_id).write(
                {
                    "state": "confirm",
                    "request_date_from": "2024-02-05",
                    "request_date_to": "2024-02-08",
                }
            )
