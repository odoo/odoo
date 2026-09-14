from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.datetime import timezone, to_timezone
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    hr_presence_ip_date = fields.Date(
        string="Last Company-IP Connection",
        groups="hr.group_hr_user",
        help="Last day this employee reached the server from an address listed "
        "in their company's valid IP addresses.",
    )
    hr_presence_email_date = fields.Date(
        string="Last Day Emails Were Sent",
        groups="hr.group_hr_user",
        help="Last day this employee sent at least the number of emails their "
        "company requires as proof of presence.",
    )
    hr_presence_manual_state = fields.Selection(
        selection=[("present", "Present"), ("absent", "Absent")],
        string="Manual Presence",
        groups="hr.group_hr_user",
        help="Presence set by hand by an HR manager. It applies to the day in "
        "Manual Presence Date and is ignored on any other day.",
    )
    hr_presence_manual_date = fields.Date(
        string="Manual Presence Date",
        groups="hr.group_hr_user",
    )

    # Stored mirror of hr_presence_state, which is computed and therefore
    # neither searchable nor groupable. It carries every value
    # hr_presence_state can take, 'archive' included, so that mirroring never
    # has to drop one.
    #
    # A plain stored field refreshed at named points, NOT a stored computed one,
    # and the reason is `user_id.im_status`: hr_presence_state depends on it,
    # and mail.presence writes and commits a status on every websocket
    # heartbeat. A computed mirror would therefore write an hr_employee row per
    # user per heartbeat -- far worse than one sweep an hour.
    #
    # So whoever changes the evidence refreshes it: create, for an employee who
    # would otherwise carry this default until the next sweep; the websocket as
    # it stamps a connection; the sweep for the emails it counted; an action for
    # a manager's override. The cron catches what is left, which is a state
    # nobody wrote -- the transitions time itself makes, and a field the state
    # reads changing under it.
    hr_presence_state_display = fields.Selection(
        selection=[
            ("out_of_working_hour", "Off-Hours"),
            ("present", "Present"),
            ("absent", "Absent"),
            ("archive", "Archived"),
        ],
        string="Presence",
        default="out_of_working_hour",
    )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        # Without this a new employee carries the field default until the next
        # sweep -- reading Absent in the icon of their own row while the Absent
        # filter, which reads the mirror, cannot see them. Six queries whatever
        # the batch size, and the same population the sweep covers.
        controlled = employees.filtered(
            lambda employee: (
                employee.company_id.hr_presence_control_email
                or employee.company_id.hr_presence_control_ip
            )
        )
        if controlled:
            self._hr_presence_refresh_display(controlled)
        return employees

    # ------------------------------------------------------------------ dates
    def _hr_presence_today(self):
        """Today in each employee's own timezone, keyed by employee id.

        A UTC day boundary puts an employee in UTC-6 at 18:00 of the previous
        local day, so evening activity counts towards the wrong date.
        """
        today_by_employee = {}
        for employee in self:
            today_by_employee[employee.id] = fields.Datetime.context_timestamp(
                employee.with_context(tz=employee.tz or "UTC"), fields.Datetime.now()
            ).date()
        return today_by_employee

    @api.model
    def _hr_presence_day_bounds_utc(self, tz_name, day):
        """The employee's own day, half-open, as naive UTC bounds.

        The end is the NEXT day's first instant, not this one's last. Built from
        `time.max` the two disagree by an hour on a day whose local midnight is
        ambiguous -- `fold=0` picks the earlier 23:59:59, so the day ends an
        hour early and that hour falls in no window at all (America/Santiago
        2026-04-04, Asia/Beirut 2026-10-25). Half-open tiles by construction.
        """
        zone = timezone(tz_name or "UTC")
        to_utc = to_timezone(None)

        def first_instant(on):
            return to_utc(datetime.combine(on, time.min).replace(tzinfo=zone))

        return first_instant(day), first_instant(day + timedelta(days=1))

    # -------------------------------------------------------------- the cron
    @api.model
    def _check_presence(self):
        """Refresh every company's presence evidence and its stored mirror.

        Runs for every company that switched a control on, not only the one the
        cron user happens to sit in: a company left out is not merely uncomputed,
        its employees keep yesterday's evidence.
        """
        with _debug.perf("check_presence", cr=self.env.cr) as span:
            companies = (
                self.env["res.company"]
                .sudo()
                .search(
                    [
                        "|",
                        ("hr_presence_control_email", "=", True),
                        ("hr_presence_control_ip", "=", True),
                    ]
                )
            )
            employees = (
                self.env["hr.employee"]
                .sudo()
                .with_context(active_test=False)
                .search([("company_id", "in", companies.ids)])
            )
            span.set(companies=len(companies), employees=len(employees))
            if not employees:
                _debug.logic("check_presence_idle", companies=len(companies))
                return
            self._hr_presence_mark_email_evidence(employees.filtered("active"))
            self._hr_presence_refresh_display(employees)

    @api.model
    def _hr_presence_mark_email_evidence(self, employees):
        """Stamp today on employees who sent enough emails in their own day.

        Only a message the employee wrote and that left the chatter counts:
        'notification' and 'auto_comment' are written by the system in their
        name, and an internal log note is not an email.

        One query covers every timezone -- the messages are read once over the
        union of the local days and bucketed here -- because a query per
        distinct timezone is a query in a loop however few timezones there are.
        """
        by_email_control = employees.filtered(
            lambda e: e.company_id.hr_presence_control_email
        )
        if not by_email_control:
            return
        today_by_employee = by_email_control._hr_presence_today()
        window_by_employee = {}
        partners = self.env["res.partner"]
        employees_by_partner = defaultdict(lambda: self.env["hr.employee"])
        for employee in by_email_control:
            partner = employee.user_id.partner_id
            if not partner:
                continue
            window_by_employee[employee.id] = self._hr_presence_day_bounds_utc(
                employee.tz, today_by_employee[employee.id]
            )
            partners |= partner
            employees_by_partner[partner.id] |= employee
        if not partners:
            return

        starts = [start for start, _end in window_by_employee.values()]
        ends = [end for _start, end in window_by_employee.values()]
        messages = (
            self.env["mail.message"]
            .sudo()
            .search_read(
                [
                    ("author_id", "in", partners.ids),
                    ("message_type", "in", ("comment", "email_outgoing")),
                    ("subtype_id.internal", "=", False),
                    ("date", ">=", min(starts)),
                    ("date", "<", max(ends)),
                ],
                ["author_id", "date"],
                load=False,
            )
        )
        sent_by_partner = defaultdict(list)
        for message in messages:
            sent_by_partner[message["author_id"]].append(message["date"])

        # Over the employees, not over the authors: a company that turned the
        # control on without setting an amount asks for a threshold of zero,
        # and an employee who wrote nothing has to be able to meet it.
        reached_by_day = defaultdict(lambda: self.env["hr.employee"])
        for partner_id, candidates in employees_by_partner.items():
            dates = sent_by_partner.get(partner_id, ())
            for employee in candidates:
                start, end = window_by_employee[employee.id]
                count = sum(1 for date in dates if start <= date < end)
                threshold = employee.company_id.hr_presence_control_email_amount
                today = today_by_employee[employee.id]
                if count >= threshold and employee.hr_presence_email_date != today:
                    reached_by_day[today] |= employee
                    _debug.logic(
                        "email_evidence",
                        employee=employee,
                        count=count,
                        threshold=threshold,
                        day=today,
                    )
        for day, records in reached_by_day.items():
            records.hr_presence_email_date = day

    @api.model
    def _hr_presence_refresh_display(self, employees):
        by_state = defaultdict(lambda: self.env["hr.employee"])
        for employee in employees:
            state = employee.hr_presence_state
            if employee.hr_presence_state_display != state:
                by_state[state] |= employee
        for state, records in by_state.items():
            records.hr_presence_state_display = state
        _debug.lifecycle(
            "display_refreshed",
            employees=len(employees),
            changed=sum(len(recs) for recs in by_state.values()),
            states=",".join(sorted(by_state)),
        )

    # ----------------------------------------------------------------- guard
    def _check_hr_manager(self):
        if not self.env.user.has_group("hr.group_hr_manager"):
            _debug.logic("presence_action_refused", user=self.env.uid)
            raise UserError(
                self.env._(
                    "You don't have the right to do this. Please contact an Administrator."
                )
            )

    # --------------------------------------------------------------- actions
    def _action_set_manual_presence(self, state):
        self._check_hr_manager()
        today_by_employee = self._hr_presence_today()
        by_day = defaultdict(lambda: self.env["hr.employee"])
        for employee in self:
            by_day[today_by_employee[employee.id]] |= employee
        for day, records in by_day.items():
            records.write(
                {
                    "hr_presence_manual_state": state,
                    "hr_presence_manual_date": day,
                    "hr_presence_state_display": state,
                }
            )
        _debug.lifecycle("manual_presence_set", employees=self, state=state)

    def action_set_present(self):
        self._action_set_manual_presence("present")

    def action_set_absent(self):
        self._action_set_manual_presence("absent")

    def action_view_leave_request(self):
        if len(self) == 1:
            model = "hr.leave"
            context = {"default_employee_id": self.id}
        else:
            model = "hr.leave.generate.multi.wizard"
            context = {
                "default_employee_ids": self.ids,
                "default_date_from": fields.Date.today(),
                "default_date_to": fields.Date.today(),
                "default_name": self.env._("Unplanned Absence"),
            }

        return {
            "type": "ir.actions.act_window",
            "res_model": model,
            "views": [[False, "form"]],
            "view_mode": "form",
            "context": context,
            "target": "new",
        }

    def action_send_sms(self):
        self._check_hr_manager()
        context = dict(self.env.context)
        context.update(
            default_res_model="hr.employee",
            default_res_ids=self.ids,
            default_composition_mode="mass",
            default_number_field_name="phone_ids",
            default_mass_keep_log=True,
        )
        template = self.env.ref(
            "hr_presence.sms_template_presence", raise_if_not_found=False
        )
        if template:
            context["default_template_id"] = template.id
        else:
            context["default_body"] = self.env._(
                "Hi, we noticed you're not at work and no time-off was submitted. "
                "If this is an oversight from us, we apologize. Please contact "
                "your manager or HR ASAP. Thanks"
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sms.composer",
            "view_mode": "form",
            "context": context,
            "name": self.env._("Send SMS"),
            "target": "new",
        }

    def action_send_email(self):
        self._check_hr_manager()
        context = dict(self.env.context)
        context.update(
            default_model="hr.employee",
            default_res_ids=self.ids,
            default_composition_mode="mass_mail",
        )
        template = self.env.ref(
            "hr_presence.mail_template_presence", raise_if_not_found=False
        )
        if template:
            context["default_template_id"] = template.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "context": context,
            "name": self.env._("Send Email"),
            "target": "new",
        }

    def action_send_log(self):
        self._check_hr_manager()
        labels = dict(
            self._fields["hr_presence_state_display"]._description_selection(self.env)
        )
        for employee in self:
            employee.message_post(
                body=self.env._(
                    "%(name)s has been noted as %(state)s today",
                    name=employee.name,
                    state=labels.get(
                        employee.hr_presence_state_display,
                        employee.hr_presence_state_display,
                    ),
                )
            )
        _debug.lifecycle("presence_logged", employees=self)

    # --------------------------------------------------------------- compute
    @api.depends(
        "active",
        "company_id.hr_presence_control_email",
        "company_id.hr_presence_control_ip",
        "hr_presence_email_date",
        "hr_presence_ip_date",
        "hr_presence_manual_date",
        "hr_presence_manual_state",
        "is_absent",
        "resource_calendar_id.flexible_hours",
        "resource_calendar_id",
        "tz",
        "user_id.im_status",
    )
    def _compute_hr_presence_state(self):
        super()._compute_hr_presence_state()
        controlled = self.filtered(
            lambda e: (
                e.active
                and (
                    e.company_id.hr_presence_control_email
                    or e.company_id.hr_presence_control_ip
                )
            )
        )
        if not controlled:
            return
        today_by_employee = controlled._hr_presence_today()
        manual = controlled.filtered(
            lambda e: (
                e.hr_presence_manual_state
                and e.hr_presence_manual_date == today_by_employee[e.id]
            )
        )
        automatic = controlled - manual
        # Narrowing twice, and neither narrowing is the guard: an override and a
        # flexible schedule both make the answer known without asking, and
        # _hr_presence_verdict is what enforces that. Removing this line changes
        # no verdict -- it only stops _work_intervals_batch being run for a
        # calendar whose answer is discarded.
        scheduled = automatic.filtered(
            lambda e: not e.resource_id.sudo()._is_flexible()
        )
        working_now = frozenset(scheduled._get_employee_ids_working_now())
        # What the chain below concluded, read before anything is overwritten.
        observed = {employee.id: employee.hr_presence_state for employee in controlled}
        for employee in controlled:
            employee.hr_presence_state = employee._hr_presence_verdict(
                today_by_employee[employee.id], working_now, observed[employee.id]
            )
        _debug.logic(
            "presence_computed",
            controlled=len(controlled),
            manual=len(manual),
            working_now=len(working_now),
            kept_observed=sum(
                1
                for employee in controlled
                if observed[employee.id] == "present"
                and employee.hr_presence_state == "present"
            ),
        )

    def _hr_presence_verdict(self, today, working_now, observed=None):
        """This module's own answer for one employee, whatever a later override
        makes of it.

        The branches are ordered by what they are made of, because that is what
        decides which may overwrite which. In the order the code runs them:

        1. a manager's override -- an explicit human decision, over everything;
        2. this module's own evidence, a company-IP connection or emails sent;
        3. `observed`, whatever the chain below concluded before this ran: a
           kiosk check-in, an online session. This module may INFER, but it may
           not overwrite an observation with a conclusion drawn from that
           observation's absence -- an employee standing at the kiosk read
           Absent because the IP they did not connect from proved nothing;
        4. abstention, where neither instrument can reach the employee at all;
        5. this module's inferences, which is everything left.

        An approved time off does not make an employee absent -- it excuses
        them. Requiring it was what put the verdict on everyone who was
        excused and on nobody who was not.
        """
        self.check_singleton()
        if self.hr_presence_manual_state and self.hr_presence_manual_date == today:
            return self.hr_presence_manual_state
        if today in (self.hr_presence_ip_date, self.hr_presence_email_date):
            return "present"
        if observed == "present":
            return "present"
        if not self.user_id:
            # Neither instrument this module has can reach an employee with no
            # login: the websocket finds employees by user_id, and the message
            # count needs their partner. Concluding an absence from evidence
            # that could never have been produced is not a verdict, it is the
            # instrument having been pointed somewhere else. Abstain, leaving
            # whatever the rest of the chain made of them.
            return observed or "out_of_working_hour"
        if self.id not in working_now or self.is_absent:
            return "out_of_working_hour"
        if self.resource_id.sudo()._is_flexible():
            # A flexible calendar with no attendance line answers every window
            # with an interval, so _get_employee_ids_working_now reports such an
            # employee as working at three in the morning. Whoever chooses their
            # own hours cannot be absent from them.
            return "out_of_working_hour"
        return "absent"
