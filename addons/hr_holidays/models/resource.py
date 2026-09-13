from datetime import UTC, datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one(
        comodel_name="hr.leave",
        string="Time Off Request",
    )
    eligible_for_accrual_rate = fields.Boolean(
        string="Eligible for Accrual Rate",
        help="If checked, this time off type will be taken into account for accruals computation.",
        default=False,
    )

    @api.constrains("date_from", "date_to", "calendar_id")
    def _check_compare_dates(self):
        dated = self.filtered(lambda leave: leave.date_from and leave.date_to)
        if not dated:
            return
        all_existing_leaves = self.env["resource.calendar.leaves"].search(
            [
                ("resource_id", "=", False),
                ("company_id", "in", dated.company_id.ids),
                ("date_from", "<=", max(dated.mapped("date_to"))),
                ("date_to", ">=", min(dated.mapped("date_from"))),
            ]
        )
        for record in dated:
            if not record.resource_id:
                existing_leaves = all_existing_leaves.filtered(
                    lambda leave, record=record: (
                        record.id != leave.id
                        and record["company_id"] == leave["company_id"]
                        and record["date_from"] <= leave["date_to"]
                        and record["date_to"] >= leave["date_from"]
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

    def _get_time_domain_dict(self):
        return [
            {
                "company_id": record.company_id.id,
                "date_from": record.date_from,
                "date_to": record.date_to,
            }
            for record in self
            if not record.resource_id
        ]

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

    def _convert_timezone(self, utc_naive_datetime, tz_from, tz_to):
        naive_datetime_from = utc_naive_datetime.astimezone(tz_from).replace(
            tzinfo=None
        )
        aware_datetime_to = naive_datetime_from.replace(tzinfo=tz_to)
        return aware_datetime_to.astimezone(UTC).replace(tzinfo=None)

    def _resolve_datetime(self, datetime_representation, date_format=None):
        if isinstance(datetime_representation, datetime):
            return datetime_representation
        elif isinstance(datetime_representation, str) and date_format:
            return datetime.strptime(datetime_representation, date_format)
        else:
            return None

    def _prepare_public_holidays_values(self, vals_list):
        for vals in vals_list:
            if (
                not vals.get("calendar_id")
                or vals.get("resource_id")
                or not isinstance(vals.get("date_from"), (datetime, str))
                or not isinstance(vals.get("date_to"), (datetime, str))
            ):
                continue
            user_tz = timezone(self.env.user.tz) if self.env.user.tz else UTC
            calendar_tz = timezone(
                self.env["resource.calendar"].browse(vals["calendar_id"]).tz
            )
            if user_tz != calendar_tz:
                datetime_from = self._resolve_datetime(
                    vals["date_from"], "%Y-%m-%d %H:%M:%S"
                )
                datetime_to = self._resolve_datetime(
                    vals["date_to"], "%Y-%m-%d %H:%M:%S"
                )
                if datetime_from and datetime_to:
                    vals["date_from"] = self._convert_timezone(
                        datetime_from, user_tz, calendar_tz
                    )
                    vals["date_to"] = self._convert_timezone(
                        datetime_to, user_tz, calendar_tz
                    )
        return vals_list

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = self._prepare_public_holidays_values(vals_list)
        res = super().create(vals_list)
        time_domain_dict = res._get_time_domain_dict()
        self._reevaluate_leaves(time_domain_dict)
        return res

    def write(self, vals):
        time_domain_dict = self._get_time_domain_dict()
        res = super().write(vals)
        time_domain_dict.extend(self._get_time_domain_dict())
        self._reevaluate_leaves(time_domain_dict)

        return res

    def unlink(self):
        time_domain_dict = self._get_time_domain_dict()
        res = super().unlink()
        self._reevaluate_leaves(time_domain_dict)

        return res

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

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env["resource.calendar.leaves"]._read_group(
            [("resource_id", "=", False), ("calendar_id", "in", self.ids)],
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
        leave_start = leave[0]
        leave_record = leave[2]
        holiday_id = leave_record.holiday_id
        tz = timezone(self.tz or self.env.user.tz)

        if holiday_id.request_unit_half:
            leave_day = leave_start.date()
            half_start_datetime = datetime.combine(
                leave_day,
                datetime.min.time()
                if holiday_id.request_date_from_period == "am"
                else time(12),
            ).replace(tzinfo=tz)
            half_end_datetime = datetime.combine(
                leave_day,
                time(12)
                if holiday_id.request_date_from_period == "am"
                else datetime.max.time(),
            ).replace(tzinfo=tz)
            ranges_to_remove.append(
                (
                    half_start_datetime,
                    half_end_datetime,
                    self.env["resource.calendar.attendance"],
                )
            )

            if not self._is_fully_flexible():
                if leave_day >= start_day and leave_day <= end_day:
                    resource_hours_per_day[self.id][leave_day] -= (
                        holiday_id.number_of_hours
                    )
                week = self._flexible_week_key(leave_day)
                resource_hours_per_week[self.id][week] -= holiday_id.number_of_hours
        elif holiday_id.request_unit_hours:
            leave_day = leave_start.date()
            range_start_datetime = leave_record.date_from.replace(
                tzinfo=UTC
            ).astimezone(tz)
            range_end_datetime = leave_record.date_to.replace(tzinfo=UTC).astimezone(tz)
            ranges_to_remove.append(
                (
                    range_start_datetime,
                    range_end_datetime,
                    self.env["resource.calendar.attendance"],
                )
            )

            if not self._is_fully_flexible():
                if leave_day >= start_day and leave_day <= end_day:
                    resource_hours_per_day[self.id][leave_day] -= (
                        holiday_id.number_of_hours
                    )
                week = self._flexible_week_key(leave_day)
                resource_hours_per_week[self.id][week] -= holiday_id.number_of_hours
        else:
            super()._format_leave(
                leave,
                resource_hours_per_day,
                resource_hours_per_week,
                ranges_to_remove,
                start_day,
                end_day,
            )
