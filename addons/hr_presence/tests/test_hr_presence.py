from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import HrPresenceCase


@tagged("post_install", "-at_install")
class TestPresenceState(HrPresenceCase):
    def test_the_module_rule_reads_as_one_function(self):
        employee = self._make_employee("readable")
        today = self._today_for(employee)
        working = frozenset([employee.id])
        self.assertEqual(employee._hr_presence_verdict(today, working), "absent")
        self.assertEqual(
            employee._hr_presence_verdict(today, frozenset()), "out_of_working_hour"
        )
        employee.hr_presence_ip_date = today
        self.assertEqual(employee._hr_presence_verdict(today, working), "present")

    def test_an_employee_at_work_with_no_sign_of_activity_is_absent(self):
        """The module's whole point: the unexcused absence is the one it flags.

        It used to require hr_holidays' is_absent, which is true only of an
        employee whose time off was APPROVED, so the verdict landed on exactly
        the people who were excused.
        """
        truant = self._make_employee("truant")
        self.assertFalse(truant.is_absent)
        self.assertEqual(truant.hr_presence_state, "absent")

    def test_an_approved_time_off_excuses_the_absence(self):
        """Asserted on this module's own verdict: hr_attendance, when it is
        installed, re-decides afterwards and marks any checked-out employee in
        working hours absent regardless of their time off."""
        excused = self._make_employee("excused")
        self._approve_leave(excused)
        excused.invalidate_recordset()
        self.assertTrue(excused.is_absent)
        self.assertEqual(self._verdict(excused), "out_of_working_hour")

    def test_an_employee_outside_working_hours_is_off_hours_not_absent(self):
        company = self.env["res.company"].create({"name": "Night Co"})
        calendar = self._make_calendar(company, "UTC", hour_from=0.0, hour_to=0.01)
        company.write(
            {
                "resource_calendar_id": calendar.id,
                "hr_presence_control_ip": True,
                "hr_presence_control_ip_list": "10.0.0.1",
            }
        )
        sleeper = self._make_employee("sleeper", company=company, calendar=calendar)
        self.assertEqual(sleeper.hr_presence_state, "out_of_working_hour")

    def test_ip_evidence_of_today_makes_an_employee_present(self):
        connected = self._make_employee("connected")
        connected.hr_presence_ip_date = self._today_for(connected)
        self.assertEqual(connected.hr_presence_state, "present")

    def test_evidence_of_a_previous_day_does_not_carry_over(self):
        """The evidence is a date, so a company the cron never reaches cannot
        keep yesterday's answer: four booleans could, until a sweep reset them."""
        stale = self._make_employee("stale")
        stale.hr_presence_ip_date = self._today_for(stale) - timedelta(days=1)
        self.assertEqual(stale.hr_presence_state, "absent")

    def test_an_archived_employee_keeps_the_archive_state(self):
        """hr sets 'archive' for an inactive employee and this module used to
        re-decide over it, making the presence_archive icon unreachable."""
        gone = self._make_employee("gone")
        gone.action_archive()
        gone.invalidate_recordset()
        self.assertEqual(gone.hr_presence_state, "archive")

    def test_the_state_moves_when_the_evidence_moves(self):
        """The compute declared neither the evidence fields nor is_absent, so a
        sweep could write its answer without the displayed state following."""
        employee = self._make_employee("watched")
        self.assertEqual(employee.hr_presence_state, "absent")
        employee.hr_presence_ip_date = self._today_for(employee)
        self.assertEqual(employee.hr_presence_state, "present")
        employee.hr_presence_ip_date = False
        self.assertEqual(employee.hr_presence_state, "absent")

    def test_a_company_with_no_control_ignores_the_evidence_entirely(self):
        plain = self.env["res.company"].create({"name": "Plain Co"})
        calendar = self._make_calendar(plain, "UTC")
        plain.resource_calendar_id = calendar
        employee = self._make_employee("plain", company=plain, calendar=calendar)
        before = employee.hr_presence_state
        employee.hr_presence_ip_date = self._today_for(employee)
        employee.invalidate_recordset()
        self.assertEqual(
            employee.hr_presence_state,
            before,
            "this module must not decide for a company that asked it not to",
        )


@tagged("post_install", "-at_install")
class TestManualOverride(HrPresenceCase):
    def test_a_manager_sets_the_presence_for_the_day(self):
        employee = self._make_employee("overridden")
        employee.with_user(self.manager).action_set_present()
        self.assertEqual(employee.hr_presence_manual_state, "present")
        self.assertEqual(employee.hr_presence_state, "present")
        employee.with_user(self.manager).action_set_absent()
        self.assertEqual(employee.hr_presence_state, "absent")

    def test_an_override_expires_with_the_day_it_was_made_for(self):
        employee = self._make_employee("yesterdays")
        employee.write(
            {
                "hr_presence_manual_state": "present",
                "hr_presence_manual_date": self._today_for(employee)
                - timedelta(days=1),
            }
        )
        self.assertEqual(employee.hr_presence_state, "absent")

    def test_an_override_outranks_the_evidence(self):
        employee = self._make_employee("vetoed")
        employee.hr_presence_ip_date = self._today_for(employee)
        employee.with_user(self.manager).action_set_absent()
        self.assertEqual(employee.hr_presence_state, "absent")

    def test_the_sweep_does_not_turn_an_automatic_present_into_a_manual_one(self):
        """write() used to stamp the manual flag on any 'present' written,
        including the one the sweep writes itself."""
        employee = self._make_employee("automatic")
        employee.hr_presence_ip_date = self._today_for(employee)
        self.env["hr.employee"]._check_presence()
        self.assertEqual(employee.hr_presence_state_display, "present")
        self.assertFalse(employee.hr_presence_manual_state)

    def test_only_an_hr_manager_may_act(self):
        employee = self._make_employee("guarded")
        plain_user = self._make_user("plain_actor", self.company)
        for action in (
            "action_set_present",
            "action_set_absent",
            "action_send_log",
            "action_send_sms",
            "action_send_email",
        ):
            with self.subTest(action=action), self.assertRaises(UserError):
                getattr(employee.with_user(plain_user), action)()


@tagged("post_install", "-at_install")
class TestEmailEvidence(HrPresenceCase):
    def test_enough_emails_sent_today_prove_presence(self):
        writer = self._make_employee("writer")
        self._post_emails(writer, 2)
        self.env["hr.employee"]._check_presence()
        self.assertEqual(writer.hr_presence_email_date, self._today_for(writer))
        self.assertEqual(writer.hr_presence_state, "present")

    def test_fewer_emails_than_the_threshold_prove_nothing(self):
        writer = self._make_employee("shy")
        self._post_emails(writer, 1)
        self.env["hr.employee"]._check_presence()
        self.assertFalse(writer.hr_presence_email_date)

    def test_an_internal_log_note_is_not_an_email(self):
        """Counting every mail.message let one internal note mark an employee
        present, and let every tracking message the system writes do the same."""
        noter = self._make_employee("noter")
        self._post_emails(noter, 5, internal=True)
        self.env["hr.employee"]._check_presence()
        self.assertFalse(noter.hr_presence_email_date)
        self.assertEqual(noter.hr_presence_state, "absent")

    def test_a_threshold_of_zero_is_met_by_writing_nothing(self):
        """An Integer with no default: turning the control on without setting an
        amount asks for zero emails, and must be answered uniformly."""
        self.company.hr_presence_control_email_amount = 0
        silent = self._make_employee("silent")
        self.env["hr.employee"]._check_presence()
        self.assertEqual(silent.hr_presence_email_date, self._today_for(silent))
        self.assertEqual(silent.hr_presence_state, "present")

    def test_a_system_notification_is_not_an_email(self):
        notified = self._make_employee("notified")
        self._post_emails(notified, 5, message_type="notification")
        self.env["hr.employee"]._check_presence()
        self.assertFalse(notified.hr_presence_email_date)


@tagged("post_install", "-at_install")
class TestDayBoundary(HrPresenceCase):
    def test_the_day_is_the_employees_own_day_not_utc(self):
        """A UTC midnight opens the window at 18:00 of the previous local day in
        UTC-6, so yesterday evening's work counted as today's."""
        company = self.env["res.company"].create({"name": "Mexico Co"})
        calendar = self._make_calendar(company, "America/Mexico_City")
        company.write(
            {
                "resource_calendar_id": calendar.id,
                "hr_presence_control_email": True,
                "hr_presence_control_email_amount": 1,
            }
        )
        employee = self._make_employee(
            "mexican", company=company, calendar=calendar, tz="America/Mexico_City"
        )
        local_today = self._today_for(employee)
        utc_today = fields.Datetime.now().date()
        start = self.env["hr.employee"]._hr_presence_day_bounds_utc(
            "America/Mexico_City", local_today
        )[0]
        self.assertEqual(
            start,
            self._utc_bounds("America/Mexico_City", local_today),
            "the window must open at local midnight, expressed in UTC",
        )
        if local_today == utc_today:
            self.assertNotEqual(
                start,
                fields.Datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
                "local midnight is not UTC midnight for a UTC-6 company",
            )


@tagged("post_install", "-at_install")
class TestSweep(HrPresenceCase):
    def test_the_sweep_mirrors_the_state_into_the_searchable_field(self):
        truant = self._make_employee("mirrored")
        self.env["hr.employee"]._check_presence()
        self.assertEqual(truant.hr_presence_state_display, "absent")
        self.assertEqual(
            self.env["hr.employee"].search(
                [("hr_presence_state_display", "=", "absent"), ("id", "=", truant.id)]
            ),
            truant,
        )

    def test_the_mirror_carries_every_state_including_archive(self):
        gone = self._make_employee("archived_mirror")
        gone.action_archive()
        self.env["hr.employee"]._check_presence()
        self.assertEqual(gone.hr_presence_state_display, "archive")

    def test_the_sweep_leaves_an_uncontrolled_company_alone(self):
        plain = self.env["res.company"].create({"name": "Untouched Co"})
        calendar = self._make_calendar(plain, "UTC")
        plain.resource_calendar_id = calendar
        employee = self._make_employee("untouched", company=plain, calendar=calendar)
        employee.hr_presence_state_display = "present"
        self.env["hr.employee"]._check_presence()
        self.assertEqual(employee.hr_presence_state_display, "present")

    def test_no_company_keeps_a_write_only_compute_stamp(self):
        """It guarded "is this evidence from today"; the evidence carries its
        own date now, and ir.cron.lastcall already says when the sweep ran."""
        self.assertNotIn(
            "hr_presence_last_compute_date", self.env["res.company"]._fields
        )


@tagged("post_install", "-at_install")
class TestActions(HrPresenceCase):
    def test_the_sms_action_reaches_the_template_this_module_ships(self):
        """The code asked for hr_presence.sms_template_presence while the data
        file shipped sms_template_data_hr_presence, so the template was dead."""
        template = self.env.ref("hr_presence.sms_template_presence")
        self.assertEqual(template.model_id.model, "hr.employee")
        employee = self._make_employee("texted")
        action = employee.with_user(self.manager).action_send_sms()
        self.assertEqual(action["context"]["default_template_id"], template.id)
        self.assertNotIn("default_body", action["context"])

    def test_the_email_action_reaches_the_template_this_module_ships(self):
        template = self.env.ref("hr_presence.mail_template_presence")
        employee = self._make_employee("mailed")
        action = employee.with_user(self.manager).action_send_email()
        self.assertEqual(action["res_model"], "mail.compose.message")
        self.assertEqual(action["context"]["default_template_id"], template.id)
        self.assertEqual(action["context"]["default_res_ids"], employee.ids)

    def test_the_log_note_names_the_state_in_words(self):
        """It used to post the technical value, e.g. 'out_of_working_hour'."""
        employee = self._make_employee("logged")
        self.env["hr.employee"]._check_presence()
        employee.with_user(self.manager).action_send_log()
        body = employee.message_ids[:1].body
        self.assertIn("Absent", body)
        self.assertNotIn("out_of_working_hour", body)

    def test_the_time_off_action_targets_one_employee_or_many(self):
        one = self._make_employee("solo")
        two = self._make_employee("duo")
        self.assertEqual(one.action_view_leave_request()["res_model"], "hr.leave")
        self.assertEqual(
            (one | two).action_view_leave_request()["res_model"],
            "hr.leave.generate.multi.wizard",
        )


@tagged("post_install", "-at_install")
class TestWebsocketGate(HrPresenceCase):
    """Recording a connection IP used to cost a res.users.log search on every
    presence heartbeat of every internal user, whether or not any company had
    asked for IP control."""

    def test_the_gate_follows_the_setting(self):
        Company = self.env["res.company"]
        self.assertTrue(Company._hr_presence_any_ip_control())
        self.env["res.company"].search([]).hr_presence_control_ip = False
        self.assertFalse(
            Company._hr_presence_any_ip_control(),
            "the ormcache must be invalidated by the field it answers about",
        )
        self.company.hr_presence_control_ip = True
        self.assertTrue(Company._hr_presence_any_ip_control())

    def test_the_valid_ip_list_tolerates_the_spacing_people_type(self):
        self.company.hr_presence_control_ip_list = " 10.0.0.1 ,10.0.0.2 ,, "
        self.assertEqual(
            self.company._hr_presence_valid_ips(), {"10.0.0.1", "10.0.0.2"}
        )
        self.company.hr_presence_control_ip_list = False
        self.assertEqual(self.company._hr_presence_valid_ips(), set())


@tagged("post_install", "-at_install")
class TestGearMenuBindings(HrPresenceCase):
    """The gear menu identifies a presence action by a field that means it.

    It used to smuggle the section through ir.actions.server.value -- a field
    documented as "what to write" for an Update Record action -- and fetch it
    with one ORM call on every gear mount.
    """

    def _presence_actions(self):
        return self.env["ir.actions.server"].search(
            [
                ("binding_model_id.model", "=", "hr.employee"),
                ("hr_presence_section", "!=", False),
            ]
        )

    def test_every_presence_action_declares_its_section(self):
        sections = {
            action.name: action.hr_presence_section
            for action in self._presence_actions()
        }
        self.assertEqual(
            sections,
            {
                "Set Present": "state",
                "Set Absent": "state",
                "Add a Log Note": "follow_up",
                "Send Email\u2026": "follow_up",
                "Send SMS\u2026": "follow_up",
                "Create a Time Off": "follow_up",
            },
        )

    def test_no_other_action_bound_to_the_employee_claims_a_section(self):
        """binding_sequence cannot stand in for the marker: hr's Create User
        and hr_skills' Resume both default to 10, the same band."""
        bound = self.env["ir.actions.server"].search(
            [("binding_model_id.model", "=", "hr.employee")]
        )
        foreign = bound - self._presence_actions()
        self.assertTrue(foreign, "fixture: some other module binds to hr.employee")
        self.assertFalse(foreign.filtered("hr_presence_section"))

    def test_the_section_travels_with_the_binding(self):
        bindings = self.env["ir.actions.actions"]._get_bindings("hr.employee")
        by_name = {a["name"]: a for a in bindings["action"]}
        self.assertEqual(by_name["Set Present"]["hr_presence_section"], "state")
        self.assertEqual(by_name["Send SMS\u2026"]["hr_presence_section"], "follow_up")
        self.assertFalse(by_name["Create User"].get("hr_presence_section"))

    def test_the_sections_order_the_submenu(self):
        actions = self._presence_actions().sorted(
            lambda a: (a.hr_presence_section != "state", a.binding_sequence)
        )
        self.assertEqual(
            actions.mapped("name"),
            [
                "Set Present",
                "Set Absent",
                "Add a Log Note",
                "Send Email\u2026",
                "Send SMS\u2026",
                "Create a Time Off",
            ],
        )


@tagged("post_install", "-at_install")
class TestUsersLogIsNoLongerUsed(HrPresenceCase):
    def test_this_module_adds_no_field_to_res_users_log(self):
        """The IP evidence used to live in a table base vacuums down to one row
        per user, which both destroyed the evidence and made login_date report a
        presence heartbeat instead of a login."""
        self.assertNotIn("ip", self.env["res.users.log"]._fields)

    def test_the_login_date_survives_the_vacuum(self):
        employee = self._make_employee("logger")
        user = employee.user_id
        self.env["res.users.log"].sudo().search([("create_uid", "=", user.id)]).unlink()
        self.env["res.users.log"].with_user(user).sudo().create({})
        user.invalidate_recordset(["login_date", "log_ids"])
        login_date = user.login_date
        self.assertTrue(login_date)
        employee.hr_presence_ip_date = self._today_for(employee)
        self.env["res.users.log"].sudo()._gc_user_logs()
        user.invalidate_recordset(["login_date", "log_ids"])
        self.assertEqual(user.login_date, login_date)
        self.assertEqual(
            employee.hr_presence_ip_date,
            self._today_for(employee),
            "the vacuum cannot reach the presence evidence any more",
        )
