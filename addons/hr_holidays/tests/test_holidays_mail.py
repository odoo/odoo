import time
from datetime import date

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tools import mute_logger

from .common import TestHrHolidaysCommon
from odoo.addons.mail.tests.common import MailCase


class TestHolidaysMail(TestHrHolidaysCommon, MailCase):
    @mute_logger("odoo.addons.base.models.ir_model", "odoo.models")
    def test_email_sent_when_approved(self):
        with freeze_time("2022-01-15"):
            self.env.ref("hr.employee_admin").tz = "Europe/Brussels"

            holiday_status_paid_time_off = self.env["hr.leave.type"].create(
                {
                    "name": "Paid Time Off",
                    "requires_allocation": True,
                    "employee_requests": False,
                    "allocation_validation_type": "hr",
                    "leave_validation_type": "both",
                    "responsible_ids": [
                        Command.link(self.env.ref("base.user_admin").id)
                    ],
                }
            )

            self.env["hr.leave.allocation"].create(
                [
                    {
                        "name": "Paid Time off for David",
                        "holiday_status_id": holiday_status_paid_time_off.id,
                        "number_of_days": 20,
                        "employee_id": self.employee_emp_id,
                        "state": "confirm",
                        "date_from": time.strftime("%Y-%m-01"),
                    }
                ]
            ).action_approve()

            self.env["hr.leave.allocation"].create(
                [
                    {
                        "name": "Paid Time off for Mitchell",
                        "holiday_status_id": holiday_status_paid_time_off.id,
                        "number_of_days": 20,
                        "employee_id": self.ref("hr.employee_admin"),
                        "state": "confirm",
                        "date_from": time.strftime("%Y-%m-01"),
                    },
                ]
            ).action_approve()

            leave_vals = {
                "name": "Sick Time Off",
                "holiday_status_id": holiday_status_paid_time_off.id,
                "request_date_from": date.today() + relativedelta(day=2),
                "request_date_to": date.today() + relativedelta(day=3),
                "employee_id": self.ref("hr.employee_admin"),
            }
            leave = self.env["hr.leave"].create(leave_vals)
            leave.action_approve()
            with self.mock_mail_gateway():
                leave.action_approve()
                admin_emails = self._new_mails.filtered(
                    lambda x: (
                        x.partner_ids.employee_ids.id == self.ref("hr.employee_admin")
                    )
                )
                self.assertEqual(
                    len(admin_emails), 1, "Mitchell Admin should receive an email"
                )
                self.assertTrue("has been accepted" in admin_emails.preview)

    def test_notify_officers_when_the_type_asks_for_it(self):
        """A type flagged to notify officers reaches every officer of the
        employee's company, without anyone maintaining a list."""
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Notifying Time Off",
                "requires_allocation": False,
                "notify_time_off_officers": True,
            }
        )
        with self.mock_mail_gateway():
            self.env["hr.leave"].create(
                {
                    "name": "Someone should hear about this",
                    "holiday_status_id": leave_type.id,
                    "employee_id": self.employee_emp_id,
                    "request_date_from": date(2026, 5, 6),
                    "request_date_to": date(2026, 5, 6),
                }
            )
        notifications = self._new_mails.filtered(
            lambda mail: "New Time Off Request" in (mail.subject or "")
        )
        self.assertTrue(notifications, "the officers were not notified")
        officers = self.env.ref(
            "hr_holidays.group_hr_holidays_user"
        ).all_user_ids.filtered(
            lambda user: self.employee_emp.company_id in user.company_ids
        )
        self.assertTrue(officers, "sanity: the fixture has officers to notify")
        self.assertEqual(
            notifications.recipient_ids,
            officers.partner_id,
            "every officer of the employee's company should be reached, and no one else",
        )

    def test_no_officer_notification_unless_the_type_asks(self):
        """The flag is off by default, so nothing changes for existing types."""
        leave_type = self.env["hr.leave.type"].create(
            {"name": "Quiet Time Off", "requires_allocation": False}
        )
        self.assertFalse(
            leave_type.notify_time_off_officers, "the flag must default to off"
        )
        with self.mock_mail_gateway():
            self.env["hr.leave"].create(
                {
                    "name": "Nobody needs to hear about this",
                    "holiday_status_id": leave_type.id,
                    "employee_id": self.employee_emp_id,
                    "request_date_from": date(2026, 5, 7),
                    "request_date_to": date(2026, 5, 7),
                }
            )
        self.assertFalse(
            self._new_mails.filtered(
                lambda mail: "New Time Off Request" in (mail.subject or "")
            ),
            "no officer notification should be sent when the flag is off",
        )
