from datetime import date, datetime, time, timedelta

from odoo import fields
from odoo.libs.datetime import timezone, to_timezone
from odoo.tests import TransactionCase


class HrPresenceCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Presence Co"})
        cls.calendar = cls._make_calendar(cls.company, "UTC")
        cls.company.write(
            {
                "resource_calendar_id": cls.calendar.id,
                "hr_presence_control_ip": True,
                "hr_presence_control_email": True,
                "hr_presence_control_email_amount": 2,
                "hr_presence_control_ip_list": "10.0.0.1, 10.0.0.2",
            }
        )
        cls.manager = cls._make_user(
            "presence_manager", cls.company, groups=["hr.group_hr_manager"]
        )
        assert cls.manager.has_group("hr.group_hr_manager"), (
            "fixture: the manager must be one"
        )

    @classmethod
    def _make_calendar(cls, company, tz, hour_from=0.0, hour_to=23.99):
        return cls.env["resource.calendar"].create(
            {
                "name": f"{company.name} {tz}",
                "tz": tz,
                "company_id": company.id,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": f"day {day}",
                            "dayofweek": str(day),
                            "hour_from": hour_from,
                            "hour_to": hour_to,
                            "day_period": "morning",
                        },
                    )
                    for day in range(7)
                ],
            }
        )

    @classmethod
    def _make_user(cls, login, company, groups=()):
        """A user whose groups this fixture chose, not the database's.

        `res.users.group_ids` carries a default, and on a database with demo
        data that default includes `hr.group_hr_manager` -- so a user created
        without saying otherwise arrives as an HR manager, and a test asserting
        that a plain user is refused passes only where demo data is absent.
        """
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            *(cls.env.ref(group).id for group in groups),
                        ],
                    )
                ],
            }
        )

    @classmethod
    def _make_employee(cls, name, company=None, calendar=None, tz="UTC", user=None):
        company = company or cls.company
        return cls.env["hr.employee"].create(
            {
                "name": name,
                "company_id": company.id,
                "user_id": (user or cls._make_user(f"u_{name}", company)).id,
                "resource_calendar_id": (calendar or cls.calendar).id,
                "tz": tz,
            }
        )

    @classmethod
    def _today_for(cls, employee):
        return fields.Datetime.context_timestamp(
            employee.with_context(tz=employee.tz or "UTC"), fields.Datetime.now()
        ).date()

    def _approve_leave(self, employee, day=None):
        day = day or fields.Date.today()
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": f"leave for {employee.name}",
                "requires_allocation": False,
                "company_id": employee.company_id.id,
            }
        )
        leave = self.env["hr.leave"].create(
            {
                "name": "absence",
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": day,
                "request_date_to": day,
            }
        )
        leave.sudo().action_approve()
        return leave

    def _post_emails(self, employee, count, internal=False, message_type="comment"):
        subtype = "mail.mt_note" if internal else "mail.mt_comment"
        messages = self.env["mail.message"]
        for index in range(count):
            messages |= employee.message_post(
                body=f"message {index}",
                author_id=employee.user_id.partner_id.id,
                message_type=message_type,
                subtype_xmlid=subtype,
            )
        return messages

    def _assert_authored(self, employee, messages, count, internal, message_type):
        """A test that says "these do not count" proves nothing if they were
        never posted -- it would pass just as well against an empty chatter."""
        self.assertEqual(len(messages), count, "fixture: messages were not posted")
        self.assertEqual(
            messages.author_id,
            employee.user_id.partner_id,
            "fixture: the employee must be the author, or the sweep never sees them",
        )
        self.assertEqual(set(messages.mapped("message_type")), {message_type})
        self.assertEqual(
            set(messages.mapped("subtype_id.internal")),
            {internal},
            "fixture: the subtype decides whether this is an internal note",
        )

    def _utc_bounds(self, tz_name, day):
        zone = timezone(tz_name)
        return to_timezone(None)(datetime.combine(day, time.min).replace(tzinfo=zone))

    def _verdict(self, employee):
        """This module's own verdict, before any later override re-decides."""
        today = self._today_for(employee)
        working_now = frozenset(employee._get_employee_ids_working_now())
        return employee._hr_presence_verdict(today, working_now)

    @staticmethod
    def _yesterday():
        return date.today() - timedelta(days=1)
