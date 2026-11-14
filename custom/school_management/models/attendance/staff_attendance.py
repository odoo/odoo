from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime, time


class UniversityStaffAttendance(models.Model):
    _name = "university.staff.attendance"
    _description = "Staff Attendance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, staff_id, id desc"

    staff_id = fields.Many2one(
        "university.teacher",
        string="Staff",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        "university.teacher",
        string="Employee",
        related="staff_id",
        store=True,
        readonly=True,
        index=True,
    )
    employee_code = fields.Char(
        string="Code",
        related="staff_id.teacher_id",
        store=True,
        readonly=True,
    )
    employee_avatar_128 = fields.Image(
        string="Avatar",
        related="staff_id.avatar_128",
        store=True,
        readonly=True,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )
    check_in = fields.Datetime(string="Check-in", tracking=True)
    check_out = fields.Datetime(string="Check-out", tracking=True)
    status = fields.Selection(
        [
            ("present", "Present"),
            ("absent", "Absent"),
            ("late", "Late"),
            ("leave", "On Leave"),
            ("official_duty", "Official Duty"),
            ("half_day", "Half Day"),
        ],
        string="Status",
        required=True,
        default="present",
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    remark = fields.Char(string="Remark", tracking=True)
    department_id = fields.Many2one(
        "university.department",
        string="Department",
        related="staff_id.department_id",
        store=True,
        readonly=True,
        index=True,
    )
    faculty_id = fields.Many2one(
        "university.faculty",
        string="Faculty",
        related="staff_id.faculty_id",
        store=True,
        readonly=True,
        index=True,
    )
    worked_hours = fields.Float(
        string="Worked Hours",
        compute="_compute_worked_hours",
        store=True,
        readonly=True,
    )
    ot_hours = fields.Float(string="OT (h)", default=0.0, tracking=True)
    is_holiday = fields.Boolean(
        string="Is Holiday",
        compute="_compute_is_holiday",
    )
    holiday_name = fields.Char(
        string="Holiday",
        compute="_compute_is_holiday",
    )
    calendar_start = fields.Datetime(
        string="Calendar Start",
        compute="_compute_calendar_dates",
        store=True,
    )
    calendar_stop = fields.Datetime(
        string="Calendar Stop",
        compute="_compute_calendar_dates",
        store=True,
    )

    _staff_date_unique = models.Constraint(
        "unique (staff_id, date)",
        "Only one staff attendance record is allowed per staff member and date.",
    )

    def _is_non_working_day(self, day):
        """Hook to determine if a given date is a non-working day (e.g. holiday)."""
        return False

    def _get_day_label(self, day):
        """Hook to get display label for a non-working day."""
        return False

    @api.depends("date", "faculty_id")
    def _compute_is_holiday(self):
        for rec in self:
            if not rec.date:
                rec.is_holiday = False
                rec.holiday_name = False
                continue
            if rec._is_non_working_day(rec.date):
                rec.is_holiday = True
                rec.holiday_name = rec._get_day_label(rec.date) or _("Non-Working Day")
                continue
            holiday = self.env["university.holiday"].search([
                ("date_start", "<=", rec.date),
                ("date_end", ">=", rec.date),
                "|",
                ("faculty_id", "=", False),
                ("faculty_id", "=", rec.faculty_id.id if rec.faculty_id else False),
            ], limit=1)
            rec.is_holiday = bool(holiday)
            rec.holiday_name = holiday.name if holiday else False

    @api.depends("staff_id", "date")
    def _compute_display_name(self):
        for attendance in self:
            staff_name = attendance.staff_id.display_name or _("Staff")
            date = fields.Date.to_string(attendance.date) if attendance.date else _("No date")
            attendance.display_name = _("%(staff)s - %(date)s") % {
                "staff": staff_name,
                "date": date,
            }

    @api.depends("status", "check_in", "check_out")
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.status in ("absent", "leave"):
                attendance.worked_hours = 0.0
            elif attendance.check_in and attendance.check_out:
                delta = fields.Datetime.to_datetime(attendance.check_out) - fields.Datetime.to_datetime(
                    attendance.check_in
                )
                attendance.worked_hours = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours = 0.0

    @api.onchange("check_out")
    def _onchange_check_out_set_ot(self):
        for attendance in self:
            if attendance.status in ("absent", "leave"):
                attendance.ot_hours = 0.0
                continue
            if not attendance.check_out:
                continue
            check_out = fields.Datetime.to_datetime(attendance.check_out)
            cutoff = datetime.combine(check_out.date(), time(17, 0))
            overtime = max(0.0, (check_out - cutoff).total_seconds() / 3600.0)
            attendance.ot_hours = round(overtime * 2) / 2

    @api.constrains("ot_hours")
    def _check_ot_hours(self):
        for attendance in self:
            if attendance.ot_hours < 0 or attendance.ot_hours > 8:
                raise ValidationError(_("Overtime must be between 0 and 8 hours."))

    @api.constrains("status", "check_in", "check_out")
    def _check_attendance_times(self):
        for attendance in self:
            if attendance.status in ("present", "late") and (
                not attendance.check_in or not attendance.check_out
            ):
                raise ValidationError(_("Present or late attendance requires check-in and check-out."))
            if attendance.check_in and attendance.check_out and attendance.check_out <= attendance.check_in:
                raise ValidationError(_("Check-out must be after check-in."))

    @api.depends("date", "check_in", "check_out", "worked_hours")
    def _compute_calendar_dates(self):
        for rec in self:
            if rec.check_in:
                rec.calendar_start = rec.check_in
            elif rec.date:
                rec.calendar_start = fields.Datetime.to_datetime(f"{rec.date} 08:00:00")
            else:
                rec.calendar_start = False

            if rec.check_out:
                rec.calendar_stop = rec.check_out
            elif rec.calendar_start:
                duration = rec.worked_hours if rec.worked_hours and rec.worked_hours > 0 else 8.0
                rec.calendar_stop = fields.Datetime.add(rec.calendar_start, hours=duration)
            else:
                rec.calendar_stop = False

    @api.constrains("check_in", "check_out")
    def _check_check_out_after_check_in(self):
        for attendance in self:
            if (
                attendance.check_in
                and attendance.check_out
                and attendance.check_out <= attendance.check_in
            ):
                raise ValidationError(_("Check-out must be after check-in."))

    def action_submit(self):
        for attendance in self:
            if attendance.state != "draft":
                raise ValidationError(_("Only draft attendance records can be submitted."))
            if (
                not self.env.su
                and not self.env.user.has_group("school_management.group_school_admin")
                and attendance.staff_id.user_id != self.env.user
            ):
                raise AccessError(_("You are not authorized to submit attendance records for other staff."))
            attendance.write({"state": "submitted"})

    def action_approve(self):
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only university administrators can approve staff attendance."))
        for attendance in self:
            if attendance.state != "submitted":
                raise ValidationError(_("Only submitted attendance records can be approved."))
            attendance.write({"state": "approved"})

    def action_reject(self):
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only university administrators can reject staff attendance."))
        for attendance in self:
            if attendance.state != "submitted":
                raise ValidationError(_("Only submitted attendance records can be rejected."))
            attendance.write({"state": "rejected"})

    def action_reset_draft(self):
        if not self.env.su and not self.env.user.has_group("school_management.group_school_admin"):
            raise AccessError(_("Only university administrators can reset attendance records to draft."))
        for attendance in self:
            if attendance.state not in ("approved", "rejected"):
                raise ValidationError(_("Only approved or rejected attendance records can be reset to draft."))
            attendance.write({"state": "draft"})

    @api.model_create_multi
    def create(self, vals_list):
        is_admin = self.env.su or self.env.user.has_group("school_management.group_school_admin")
        is_attendance_manager = is_admin or self.env.user.has_group("base.group_system")
        teacher_group = self.env.user.has_group("school_management.group_school_teacher")
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if vals.get("date") and fields.Date.to_date(vals["date"]) < today and not is_attendance_manager:
                raise AccessError(_("Only attendance managers can create records for past dates."))
            if not is_admin:
                if vals.get("state") and vals.get("state") != "draft":
                    raise AccessError(_("Only university administrators can set approval status directly."))
                vals["state"] = "draft"
                staff_id = vals.get("staff_id")
                if staff_id and teacher_group:
                    staff = self.env["university.teacher"].browse(staff_id)
                    if staff.user_id != self.env.user:
                        raise AccessError(_("You are only authorized to record your own staff attendance."))
        return super().create(vals_list)

    @api.model
    def action_generate_today_sheet(self):
        """Create missing attendance rows for all active staff in one batch."""
        today = fields.Date.context_today(self)
        teachers = self.env["university.teacher"].search([("active", "=", True)], order="name")
        existing = self.search([("staff_id", "in", teachers.ids), ("date", "=", today)])
        existing_ids = set(existing.mapped("staff_id").ids)
        vals_list = [
            {
                "staff_id": teacher.id,
                "date": today,
                "status": "present",
                "check_in": f"{today} 09:00:00",
                "check_out": f"{today} 17:00:00",
                "state": "draft",
            }
            for teacher in teachers
            if teacher.id not in existing_ids
        ]
        if vals_list:
            self.create(vals_list)
        return True

    def action_mark_all_present(self):
        """Mark the selected sheet rows present in one write."""
        if not self:
            return True
        today = fields.Date.context_today(self)
        self.write({
            "status": "present",
            "check_in": f"{today} 09:00:00",
            "check_out": f"{today} 17:00:00",
            "ot_hours": 0.0,
        })
        return True

    def write(self, vals):
        is_admin = self.env.su or self.env.user.has_group("school_management.group_school_admin")
        is_attendance_manager = is_admin or self.env.user.has_group("base.group_system")
        business_fields = {"staff_id", "date", "status", "check_in", "check_out", "ot_hours", "remark"}
        has_business_changes = bool(business_fields.intersection(vals.keys()))

        allowed_transitions = {
            "draft": {"draft", "submitted"},
            "submitted": {"submitted", "approved", "rejected"},
            "approved": {"approved", "draft"},
            "rejected": {"rejected", "draft"},
        }

        for record in self:
            if (
                has_business_changes
                and record.date
                and record.date < fields.Date.context_today(self)
                and not is_attendance_manager
            ):
                raise AccessError(_("Only attendance managers can edit past dates."))
            # 1. Approved record locking
            if record.state == "approved" and has_business_changes:
                raise UserError(
                    _("Cannot modify an approved attendance record. An administrator must reset it to Draft first.")
                )

            # 2. State transition validation and permission checking
            if "state" in vals:
                new_state = vals["state"]
                valid_targets = allowed_transitions.get(record.state, set())
                if new_state not in valid_targets:
                    raise ValidationError(
                        _("Invalid state transition from %(current)s to %(new)s.",
                          current=record.state,
                          new=new_state)
                    )
                if not is_admin:
                    if new_state in ("approved", "rejected", "draft"):
                        raise AccessError(_("Only university administrators can approve, reject, or reset attendance."))
                    if new_state == "submitted" and record.staff_id.user_id != self.env.user:
                        raise AccessError(_("You are not authorized to submit attendance for other staff."))

            # 3. Non-admin write permissions
            if not is_admin:
                if record.staff_id.user_id != self.env.user:
                    raise AccessError(_("You are not authorized to edit this staff attendance record."))
                if record.state in ("submitted", "approved", "rejected") and has_business_changes:
                    raise UserError(_("Cannot modify attendance records once submitted. Please contact an administrator."))

        return super().write(vals)

    @api.model
    def get_monthly_attendance_matrix(self, year=None, month=None, department_id=None, staff_id=None):
        import calendar
        from datetime import date, datetime, timedelta
        import pytz

        today = fields.Date.context_today(self)
        today_date = fields.Date.to_date(today)
        year = int(year) if year else today_date.year
        month = int(month) if month else today_date.month

        num_days = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        day_names_abbr = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        days = []
        for d in range(1, num_days + 1):
            cur_d = date(year, month, d)
            weekday_idx = cur_d.weekday()
            is_weekend = weekday_idx in (5, 6)
            days.append({
                "day_num": d,
                "day_name": day_names_abbr[weekday_idx],
                "date_str": cur_d.strftime("%Y-%m-%d"),
                "is_weekend": is_weekend,
                "is_today": cur_d == today_date,
            })

        holidays = self.env["university.holiday"].search([
            ("date_start", "<=", end_date),
            ("date_end", ">=", start_date),
        ])
        holiday_dates = set()
        for h in holidays:
            h_start = max(h.date_start, start_date)
            h_end = min(h.date_end, end_date)
            cur = h_start
            while cur <= h_end:
                holiday_dates.add(cur.strftime("%Y-%m-%d"))
                cur += timedelta(days=1)

        teacher_domain = [("active", "=", True)]
        if department_id and department_id != "all":
            teacher_domain.append(("department_id", "=", int(department_id)))
        if staff_id and staff_id != "all":
            teacher_domain.append(("id", "=", int(staff_id)))

        teachers = self.env["university.teacher"].search(teacher_domain, order="name asc")

        teacher_ids = teachers.ids
        att_domain = [
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("staff_id", "in", teacher_ids),
        ]
        attendances = self.search(att_domain)

        att_by_teacher_date = {}
        for att in attendances:
            key = (att.staff_id.id, fields.Date.to_string(att.date))
            att_by_teacher_date[key] = {
                "id": att.id,
                "status": att.status,
                "worked_hours": round(att.worked_hours, 2) if att.worked_hours else 0.0,
                "check_in": fields.Datetime.to_string(att.check_in) if att.check_in else False,
                "check_out": fields.Datetime.to_string(att.check_out) if att.check_out else False,
                "state": att.state,
            }

        staff_rows = []
        for t in teachers:
            t_days = {}
            present_cnt = 0
            absent_cnt = 0
            leave_cnt = 0
            total_hours = 0.0

            for d_info in days:
                d_str = d_info["date_str"]
                rec = att_by_teacher_date.get((t.id, d_str))
                is_hol = d_str in holiday_dates

                if rec:
                    st = rec["status"]
                    wh = rec["worked_hours"]
                    total_hours += wh
                    if st == "present":
                        present_cnt += 1
                        display_val = f"{wh:.1f}" if wh > 0 else "9.0"
                        cell_type = "worked"
                    elif st == "absent":
                        absent_cnt += 1
                        display_val = "A"
                        cell_type = "absent"
                    elif st in ("leave", "official_duty"):
                        leave_cnt += 1
                        display_val = "L"
                        cell_type = "leave"
                    elif st == "half_day":
                        present_cnt += 1
                        display_val = f"{wh:.1f}" if wh > 0 else "H"
                        cell_type = "half_day"
                    else:
                        present_cnt += 1
                        display_val = f"{wh:.1f}" if wh > 0 else "9.0"
                        cell_type = "worked"
                else:
                    if d_info["is_weekend"]:
                        display_val = "W"
                        cell_type = "weekend"
                    elif is_hol:
                        display_val = "H"
                        cell_type = "holiday"
                    else:
                        display_val = ""
                        cell_type = "empty"

                t_days[d_str] = {
                    "record_id": rec["id"] if rec else False,
                    "status": rec["status"] if rec else False,
                    "worked_hours": rec["worked_hours"] if rec else 0.0,
                    "display": display_val,
                    "cell_type": cell_type,
                    "is_weekend": d_info["is_weekend"],
                    "is_holiday": is_hol,
                }

            position_label = dict(t._fields["position"].selection).get(t.position, "") if t.position else ""
            if not position_label and t.department_id:
                position_label = t.department_id.name

            staff_rows.append({
                "id": t.id,
                "name": t.name,
                "code": t.teacher_id or "",
                "position": position_label,
                "department_id": t.department_id.id if t.department_id else False,
                "department_name": t.department_id.name if t.department_id else "",
                "has_image": bool(t.image_1920),
                "days": t_days,
                "summary": {
                    "present_count": present_cnt,
                    "absent_count": absent_cnt,
                    "leave_count": leave_cnt,
                    "total_hours": round(total_hours, 1),
                },
            })

        all_departments = self.env["university.department"].search_read(
            [("active", "=", True)], ["id", "name"], order="name asc"
        )
        all_teachers = self.env["university.teacher"].search_read(
            [("active", "=", True)], ["id", "name", "department_id"], order="name asc"
        )

        user_tz = self.env.user.tz or "UTC"
        now_dt = datetime.now(pytz.timezone(user_tz))
        hour = now_dt.hour
        if hour < 12:
            greet = _("Good Morning")
        elif hour < 17:
            greet = _("Good Afternoon")
        else:
            greet = _("Good Evening")
        greeting = f"{greet} , {self.env.user.name} ."
        time_str = now_dt.strftime("%b %d %I:%M %p")

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        current_year = today_date.year
        available_years = list(range(current_year - 2, current_year + 3))

        return {
            "year": year,
            "month": month,
            "month_name": month_names[month - 1],
            "greeting": greeting,
            "current_time_str": time_str,
            "days": days,
            "rows": staff_rows,
            "departments": all_departments,
            "staff_list": all_teachers,
            "available_years": available_years,
            "available_months": [{"num": i + 1, "name": name} for i, name in enumerate(month_names)],
        }

    @api.model
    def quick_update_attendance_cell(self, staff_id, date, status, worked_hours=9.0):
        self.check_access("write")
        rec = self.search([("staff_id", "=", int(staff_id)), ("date", "=", date)], limit=1)
        if rec:
            rec.write({
                "status": status,
                "worked_hours": worked_hours if status == "present" else 0.0,
            })
            return rec.id
        else:
            rec = self.create({
                "staff_id": int(staff_id),
                "date": date,
                "status": status,
                "worked_hours": worked_hours if status == "present" else 0.0,
                "state": "draft",
            })
            return rec.id

