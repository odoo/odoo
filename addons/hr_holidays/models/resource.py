from datetime import UTC

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone


class ResourceScheduleException(models.Model):
    _inherit = "resource.schedule.exception"

    holiday_id = fields.Many2one(
        comodel_name="hr.leave",
        string="Time Off Request",
    )
    eligible_for_accrual_rate = fields.Boolean(
        string="Eligible for Accrual Rate",
        default=False,
        help="If checked, this time off type will be taken into account for accruals computation.",
    )

    @api.model
    def _get_domain_projection(self, record):
        if record._name == "hr.leave":
            return Domain("holiday_id", "=", record.id)
        return super()._get_domain_projection(record)

    @api.model
    def _prepare_projection_link_vals(self, record):
        if record._name == "hr.leave":
            return {"holiday_id": record.id}
        return super()._prepare_projection_link_vals(record)

    @api.constrains("date_from", "date_to", "calendar_id")
    def _check_compare_dates(self):
        dated = self.filtered(lambda leave: leave.date_from and leave.date_to)
        if not dated:
            return
        all_existing_leaves = self.search(
            self._get_domain_public_holidays(
                min(dated.mapped("date_from")),
                max(dated.mapped("date_to")),
                companies=dated.company_id,
            )
        )
        for record in dated:
            if not record.resource_id:
                existing_leaves = all_existing_leaves.filtered(
                    lambda leave, record=record: (
                        record.id != leave.id
                        and record["company_id"] == leave["company_id"]
                        and record["date_from"] < leave["date_to"]
                        and record["date_to"] > leave["date_from"]
                    )
                )
                if record.calendar_id:
                    existing_leaves = existing_leaves.filtered(
                        lambda l, record=record: (
                            not l.calendar_id or l.calendar_id == record.calendar_id
                        )
                    )
                if existing_leaves:
                    raise ValidationError(
                        _(
                            "Two public holidays cannot overlap each other for the same working hours."
                        )
                    )

    def _get_domain_for_periods(self, time_domain_dict):
        return Domain.OR(
            [
                ("employee_company_id", "=", date["company_id"]),
                ("date_to", ">", date["date_from"]),
                ("date_from", "<", date["date_to"]),
            ]
            for date in time_domain_dict
        ) & Domain("state", "not in", ["refuse", "cancel"])

    def _reevaluate_leaves(self, time_domain_dict):
        if not time_domain_dict:
            return
        time_domain_dict = list(
            {tuple(sorted(entry.items())): entry for entry in time_domain_dict}.values()
        )

        domain = self._get_domain_for_periods(time_domain_dict)
        leaves = self.env["hr.leave"].search(domain)
        if not leaves:
            return

        previous_durations = leaves.mapped("number_of_days")
        previous_states = leaves.mapped("state")
        self.env.add_to_compute(self.env["hr.leave"]._fields["number_of_days"], leaves)
        self.env.add_to_compute(
            self.env["hr.leave"]._fields["duration_display"], leaves
        )
        leaves.sudo().write(
            {
                "state": "confirm",
            }
        )
        sick_time_status = self.env.ref(
            "hr_holidays.leave_type_sick_time_off", raise_if_not_found=False
        )
        leaves_to_recreate = self.env["hr.leave"]
        for previous_duration, leave, state in zip(
            previous_durations, leaves, previous_states, strict=False
        ):
            duration_difference = previous_duration - leave.number_of_days
            message = False
            if duration_difference > 0 and leave.holiday_status_id.requires_allocation:
                message = _(
                    "Due to a change in global time offs, you have been granted %s day(s) back.",
                    duration_difference,
                )
            if leave.number_of_days > previous_duration and (
                not sick_time_status or leave.holiday_status_id not in sick_time_status
            ):
                message = _(
                    "Due to a change in global time offs, %s extra day(s) have been taken from your allocation. Please review this leave if you need it to be changed.",
                    -1 * duration_difference,
                )
            try:
                leave.sudo().write({"state": state})
                leave._check_validity()
                if leave.state == "validate":
                    leaves_to_recreate |= leave
            except ValidationError:
                leave.action_refuse()
                message = _(
                    "Due to a change in global time offs, this leave no longer has the required amount of available allocation and has been set to refused. Please review this leave."
                )
            if message:
                leave._notify_change(message)
        leaves_to_recreate.sudo()._create_resource_leave()

    @api.model
    def _on_schedule_changed(self, scopes):
        super()._on_schedule_changed(scopes)
        self._reevaluate_leaves(
            [
                {
                    "company_id": scope["company_id"],
                    "date_from": scope["date_from"],
                    "date_to": scope["date_to"],
                }
                for scope in scopes
                if not scope["resource_id"]
            ]
        )

    @api.depends("holiday_id.employee_id.company_id")
    def _compute_company_id(self):
        super()._compute_company_id()
        for leave in self:
            if leave.holiday_id.employee_id.company_id:
                leave.company_id = leave.holiday_id.employee_id.company_id


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer(
        string="Time Off Count",
        compute="_compute_associated_leaves_count",
    )

    def _handle_flexible_leave_interval(self, dt0, dt1, leave):
        holiday = leave.sudo().holiday_id
        if holiday.request_unit_half or holiday.request_unit_hours:
            return dt0, dt1
        return super()._handle_flexible_leave_interval(dt0, dt1, leave)

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env["resource.schedule.exception"]._read_group(
            self.env["resource.schedule.exception"]._get_domain_public_holidays(
                calendars=self
            ),
            ["calendar_id"],
            ["__count"],
        )
        result = {
            calendar.id if calendar else "global": count
            for calendar, count in leaves_read_group
        }
        global_leave_count = result.get("global", 0)
        for calendar in self:
            calendar.associated_leaves_count = (
                result.get(calendar.id, 0) + global_leave_count
            )


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    leave_date_to = fields.Date(related="user_id.leave_date_to")

    def _format_leave(
        self,
        leave,
        resource_hours_per_day,
        resource_hours_per_week,
        ranges_to_remove,
        start_day,
        end_day,
    ):
        if len(leave[2]) > 1:
            for record in leave[2]:
                start = max(leave[0], record.date_from.replace(tzinfo=UTC))
                stop = min(leave[1], record.date_to.replace(tzinfo=UTC))
                if start < stop:
                    self._format_leave(
                        (start, stop, record),
                        resource_hours_per_day,
                        resource_hours_per_week,
                        ranges_to_remove,
                        start_day,
                        end_day,
                    )
            return
        holiday_id = leave[2].holiday_id
        if not (holiday_id.request_unit_half or holiday_id.request_unit_hours):
            super()._format_leave(
                leave,
                resource_hours_per_day,
                resource_hours_per_week,
                ranges_to_remove,
                start_day,
                end_day,
            )
            return

        attendances = self.env["resource.calendar.attendance"]
        tz = timezone(self.tz or self.env.user.tz)
        for day, window_start, window_stop, hours in holiday_id._daily_windows(tz):
            ranges_to_remove.append((window_start, window_stop, attendances))
            if self._is_fully_flexible():
                continue
            if start_day <= day <= end_day:
                resource_hours_per_day[self.id][day] -= hours
            resource_hours_per_week[self.id][self._flexible_week_key(day)] -= hours
