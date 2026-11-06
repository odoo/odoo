import logging
from datetime import datetime, time, timedelta
import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class UniversityTimetableGenerationWizard(models.TransientModel):
    _name = "university.timetable.generation.wizard"
    _description = "Timetable Generation Wizard"

    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        required=True,
        domain="[('active', '=', True)]",
    )
    semester_id = fields.Many2one(
        "university.semester",
        string="Semester",
        required=True,
        domain="[('active', '=', True), ('academic_year_id', '=', academic_year_id)]",
    )
    section_ids = fields.Many2many(
        "university.class.section",
        "university_timetable_generation_section_rel",
        "wizard_id",
        "section_id",
        string="Class Sections",
        domain="[('active', '=', True), ('semester_id', '=', semester_id)]",
    )
    timeslot_ids = fields.Many2many(
        "university.timeslot",
        "university_timetable_generation_timeslot_rel",
        "wizard_id",
        "timeslot_id",
        string="Timeslots",
        domain="[('active', '=', True)]",
    )
    start_date = fields.Date(
        string="Week Start Date",
        default=fields.Date.context_today,
        required=True,
    )
    week_count = fields.Integer(string="Weeks", default=1, required=True)
    sessions_per_week = fields.Integer(
        string="Sessions per Week",
        default=1,
        required=True,
        help="Number of distinct timeslots each subject receives per week.",
    )
    replace_existing_drafts = fields.Boolean(
        string="Replace Existing Drafts",
        default=False,
        help="Delete existing draft timetable slots (without attendance) for selected sections within the generated date range.",
    )


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "academic_year_id" in fields_list and not res.get("academic_year_id"):
            current_year = self.env["university.academic.year"].search(
                [("current", "=", True), ("active", "=", True)], limit=1
            )
            if not current_year:
                current_year = self.env["university.academic.year"].search(
                    [("active", "=", True)], limit=1
                )
            if current_year:
                res["academic_year_id"] = current_year.id
                if "semester_id" in fields_list and not res.get("semester_id"):
                    active_sem = self.env["university.semester"].search(
                        [
                            ("academic_year_id", "=", current_year.id),
                            ("active", "=", True),
                            ("is_active", "=", True),
                        ],
                        limit=1,
                    )
                    if not active_sem:
                        active_sem = self.env["university.semester"].search(
                            [
                                ("academic_year_id", "=", current_year.id),
                                ("active", "=", True),
                            ],
                            limit=1,
                        )
                    if active_sem:
                        res["semester_id"] = active_sem.id
                        if active_sem.date_start and not res.get("start_date"):
                            res["start_date"] = active_sem.date_start
        return res

    @api.onchange("academic_year_id")
    def _onchange_academic_year_id(self):
        if (
            self.semester_id
            and self.academic_year_id
            and self.semester_id.academic_year_id != self.academic_year_id
        ):
            self.semester_id = False
        self.section_ids = False

    @api.onchange("semester_id")
    def _onchange_semester_id(self):
        self.section_ids = False
        if self.semester_id:
            if not self.academic_year_id:
                self.academic_year_id = self.semester_id.academic_year_id
            if self.semester_id.date_start:
                self.start_date = self.semester_id.date_start
            if self.semester_id.date_start and self.semester_id.date_end:
                duration_days = (self.semester_id.date_end - self.semester_id.date_start).days + 1
                weeks = max(1, min(20, round(duration_days / 7.0)))
                self.week_count = weeks

    @api.constrains("week_count")
    def _check_week_count(self):
        for wizard in self:
            if wizard.week_count < 1 or wizard.week_count > 20:
                raise ValidationError(_("Generate between 1 and 20 weeks at a time."))

    @api.constrains("sessions_per_week", "timeslot_ids")
    def _check_sessions_per_week(self):
        for wizard in self:
            if any(s.schedule_line_ids for s in wizard.section_ids):
                continue
            if wizard.sessions_per_week < 1:
                raise ValidationError(_("Sessions per week must be at least 1."))
            if wizard.timeslot_ids and wizard.sessions_per_week > len(wizard.timeslot_ids):
                raise ValidationError(
                    _("Sessions per week (%(sessions)d) cannot exceed the number of selected timeslots (%(slots)d).")
                    % {"sessions": wizard.sessions_per_week, "slots": len(wizard.timeslot_ids)}
                )

    def _get_excluded_dates(self, date_start, date_end):
        """Hook for extension modules (e.g. school_public_holiday) to exclude dates from timetable generation."""
        return set()

    def _find_holiday(self, target_date, holidays, section=None):
        if not holidays:
            return None
        faculty = (
            section.program_id.department_id.faculty_id
            if section and section.program_id and section.program_id.department_id
            else False
        )
        for h in holidays:
            if h.date_start <= target_date <= h.date_end:
                if not h.faculty_id or (faculty and h.faculty_id == faculty):
                    return h
        return None

    def _create_series(self, base_vals, timeslot, monday, holidays=None, section=None, subject=None, excluded_dates=None):
        Slot = self.env["university.timetable.slot"]
        if excluded_dates is None:
            date_end = monday + timedelta(days=self.week_count * 7)
            excluded_dates = self._get_excluded_dates(monday, date_end)
        try:
            with self.env.cr.savepoint():
                records = Slot
                holiday_skips = []
                for week in range(self.week_count):
                    target_date = monday + timedelta(days=int(timeslot.day_of_week) + week * 7)
                    if target_date in excluded_dates:
                        subj_name = subject.display_name if subject else "Session"
                        sec_name = section.display_name if section else ""
                        holiday_skips.append(
                            f"{sec_name} / {subj_name} on {target_date} skipped (Public Holiday)"
                        )
                        continue
                    holiday = self._find_holiday(target_date, holidays, section)
                    if holiday:
                        subj_name = subject.display_name if subject else "Session"
                        sec_name = section.display_name if section else ""
                        holiday_skips.append(
                            f"{sec_name} / {subj_name} on {target_date} skipped (Holiday: {holiday.name})"
                        )
                        continue
                    start, end = timeslot._datetime_for_week(monday, week)
                    records |= Slot.create(dict(
                        base_vals,
                        timeslot_id=timeslot.id,
                        start_time=start,
                        end_time=end,
                    ))
                return records, None, holiday_skips
        except ValidationError as exc:
            return Slot, exc.args[0], []

    def action_generate_timetable(self):
        if not (self.env.user.has_group("school_management.group_school_admin") or self.env.user.has_group("school_management.group_school_timetable_manager")):
            raise AccessError(_("Only University Administrators can schedule a timetable."))
        self.ensure_one()
        if self.semester_id.academic_year_id != self.academic_year_id:
            raise UserError(_("The semester must belong to the selected academic year."))
        if not self.section_ids:
            raise UserError(_("Select at least one class section."))

        sections_with_lines = self.section_ids.filtered(lambda s: s.schedule_line_ids)
        if not self.timeslot_ids and not sections_with_lines:
            raise UserError(_("Select at least one timeslot or configure Weekly Schedule lines on the class sections."))

        created = self.env["university.timetable.slot"]
        skipped = []
        conflicts = []
        holiday_skipped_count = 0
        kept_existing_count = 0

        Slot = self.env["university.timetable.slot"]
        holidays = self.env["university.holiday"].search([
            ("academic_year_id", "=", self.academic_year_id.id),
        ])

        # Branch A: Class sections with configured Weekly Schedule Lines (Requirement 7)
        if sections_with_lines:
            for section in sections_with_lines:
                active_lines = section.schedule_line_ids.filtered("active")
                if not active_lines:
                    skipped.append(_("%(section)s has no active weekly schedule lines.") % {"section": section.display_name})
                    continue

                term_start = section.semester_id.date_start or self.start_date
                term_end = section.semester_id.date_end or (term_start + timedelta(days=self.week_count * 7 - 1))

                excluded_dates = self._get_excluded_dates(term_start, term_end)

                if self.replace_existing_drafts:
                    user_tz = pytz.timezone(self.env.user.tz or "UTC")
                    dt_start = user_tz.localize(datetime.combine(term_start, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
                    dt_end = user_tz.localize(datetime.combine(term_end + timedelta(days=1), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
                    existing_drafts = Slot.search([
                        ("section_id", "=", section.id),
                        ("generation_state", "=", "draft"),
                        ("state", "not in", ("done", "completed")),
                        ("status", "!=", "completed"),
                        ("start_time", ">=", dt_start),
                        ("start_time", "<", dt_end),
                    ])
                    # Preserve sessions that have recorded attendance
                    drafts_to_unlink = existing_drafts.filtered(lambda s: not s.has_attendance)
                    if drafts_to_unlink:
                        drafts_to_unlink.unlink()

                curr_date = term_start
                while curr_date <= term_end:
                    curr_weekday = str(curr_date.weekday())
                    lines_for_day = active_lines.filtered(lambda l: l.weekday == curr_weekday)

                    if lines_for_day:
                        # Check public holiday
                        if curr_date in excluded_dates or self._find_holiday(curr_date, holidays, section):
                            holiday_skipped_count += len(lines_for_day)
                            curr_date += timedelta(days=1)
                            continue

                        for line in lines_for_day:
                            start_dt, end_dt = line.timeslot_id._datetime_for_date(curr_date)
                            # Idempotency check: don't create duplicate sessions
                            existing = Slot.search([
                                ("section_id", "=", section.id),
                                ("start_time", "=", start_dt),
                                ("end_time", "=", end_dt),
                                ("state", "!=", "cancelled"),
                            ], limit=1)
                            if existing:
                                kept_existing_count += 1
                                continue

                            teacher = line.teacher_id or section.teacher_id
                            room = line.room_id or section.classroom_id

                            # Conflict checks:
                            # 1. Teacher conflict
                            if teacher and Slot.sudo().search_count([
                                ("state", "!=", "cancelled"),
                                ("teacher_id", "=", teacher.id),
                                ("start_time", "<", end_dt),
                                ("end_time", ">", start_dt),
                            ]):
                                conf_msg = _("Teacher '%(teacher)s' is already scheduled on %(date)s during %(slot)s.") % {
                                    "teacher": teacher.name,
                                    "date": curr_date,
                                    "slot": line.timeslot_id.name,
                                }
                                conflicts.append(conf_msg)
                                continue

                            # 2. Room conflict
                            if room and Slot.sudo().search_count([
                                ("state", "!=", "cancelled"),
                                ("classroom_id", "=", room.id),
                                ("start_time", "<", end_dt),
                                ("end_time", ">", start_dt),
                            ]):
                                conf_msg = _("Room '%(room)s' is already occupied on %(date)s during %(slot)s.") % {
                                    "room": room.name,
                                    "date": curr_date,
                                    "slot": line.timeslot_id.name,
                                }
                                conflicts.append(conf_msg)
                                continue

                            # 3. Student schedule conflict (warn)
                            enrolled_students = section.enrollment_ids.filtered(
                                lambda e: e.status in ("enrolled", "draft")
                            ).mapped("student_id")
                            if enrolled_students:
                                overlap_other_slots = Slot.search([
                                    ("section_id", "!=", section.id),
                                    ("state", "!=", "cancelled"),
                                    ("start_time", "<", end_dt),
                                    ("end_time", ">", start_dt),
                                ])
                                for o_slot in overlap_other_slots:
                                    o_students = o_slot.section_id.enrollment_ids.filtered(
                                        lambda e: e.status in ("enrolled", "draft")
                                    ).mapped("student_id")
                                    common = set(enrolled_students.ids) & set(o_students.ids)
                                    if common:
                                        names = ", ".join(self.env["university.student"].browse(common).mapped("name"))
                                        warn_msg = _("Student warning on %(date)s: %(students)s enrolled in both '%(s1)s' and '%(s2)s'.") % {
                                            "date": curr_date,
                                            "students": names,
                                            "s1": section.display_name,
                                            "s2": o_slot.section_id.display_name,
                                        }
                                        _logger.warning(warn_msg)
                                        conflicts.append(warn_msg)

                            # 4. Room capacity warning
                            if room and section.capacity and room.capacity and room.capacity < section.capacity:
                                _logger.warning(
                                    "Room capacity warning: Room '%s' capacity (%d) is smaller than section '%s' capacity (%d).",
                                    room.name, room.capacity, section.name, section.capacity,
                                )

                            # Create session
                            slot_vals = {
                                "class_id": section.id,
                                "section_id": section.id,
                                "subject_id": section.subject_id.id,
                                "teacher_id": teacher.id if teacher else False,
                                "classroom_id": room.id if room else False,
                                "timeslot_id": line.timeslot_id.id,
                                "start_time": start_dt,
                                "end_time": end_dt,
                                "generation_state": "draft",
                                "state": "scheduled",
                            }
                            try:
                                with self.env.cr.savepoint():
                                    new_slot = Slot.create(slot_vals)
                                    created |= new_slot
                            except ValidationError as err:
                                conflicts.append(str(err))

                    curr_date += timedelta(days=1)

        # Branch B: Fallback for sections without schedule lines (e.g. existing tests / legacy usage)
        sections_without_lines = self.section_ids - sections_with_lines
        if sections_without_lines and self.timeslot_ids:
            week_start = fields.Date.to_date(self.start_date)
            monday = week_start - timedelta(days=week_start.weekday())
            date_start = monday
            date_end = monday + timedelta(days=self.week_count * 7)
            excluded_dates = self._get_excluded_dates(date_start, date_end)

            user_tz = pytz.timezone(self.env.user.tz or "UTC")
            if self.replace_existing_drafts:
                dt_start = user_tz.localize(datetime.combine(monday, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
                dt_end = user_tz.localize(datetime.combine(monday + timedelta(days=self.week_count * 7), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
                existing_drafts = Slot.search([
                    ("section_id", "in", sections_without_lines.ids),
                    ("generation_state", "=", "draft"),
                    ("state", "not in", ("done", "completed")),
                    ("status", "!=", "completed"),
                    ("start_time", ">=", dt_start),
                    ("start_time", "<", dt_end),
                ])
                drafts_to_unlink = existing_drafts.filtered(lambda s: not s.has_attendance)
                if drafts_to_unlink:
                    drafts_to_unlink.unlink()

            slots = self.timeslot_ids.sorted(lambda item: (item.day_of_week, item.start_hour))
            for section in sections_without_lines:
                slot_index = 0
                subjects = section.subject_id or section.program_id.subject_ids
                if not subjects:
                    skipped.append("%s has no subjects" % section.display_name)
                    continue
                for subject in subjects:
                    teacher = section.teacher_id or subject.teacher_ids[:1]
                    if not teacher:
                        skipped.append("%s / %s has no teacher" % (section.display_name, subject.display_name))
                        continue

                    base_vals = {
                        "teacher_id": teacher.id,
                        "section_id": section.id,
                        "class_id": section.id,
                        "subject_id": subject.id,
                        "classroom_id": section.classroom_id.id,
                        "location": section.classroom_id.name,
                        "generation_state": "draft",
                        "state": "scheduled",
                    }

                    chosen_slots = self.env["university.timeslot"]
                    for session_num in range(self.sessions_per_week):
                        for offset in range(len(slots)):
                            candidate_slot = slots[(slot_index + offset) % len(slots)]
                            if candidate_slot in chosen_slots:
                                continue
                            records, err, holiday_skips = self._create_series(
                                base_vals, candidate_slot, monday,
                                holidays=holidays, section=section, subject=subject,
                                excluded_dates=excluded_dates
                            )
                            if not err:
                                created |= records
                                chosen_slots |= candidate_slot
                                slot_index += offset + 1
                                holiday_skipped_count += len(holiday_skips)
                                skipped.extend(holiday_skips)
                                break
                        else:
                            session_label = (
                                f" (session {session_num + 1}/{self.sessions_per_week})"
                                if self.sessions_per_week > 1
                                else ""
                            )
                            skipped.append(
                                "%s / %s%s: No conflict-free timeslot available."
                                % (section.display_name, subject.display_name, session_label)
                            )

        # Result Summary Logging & Action
        _logger.info(
            "Timetable generation complete: %d created, %d kept existing, %d holiday-skipped, %d conflicts, %d other skips.",
            len(created), kept_existing_count, holiday_skipped_count, len(conflicts), len(skipped),
        )

        if not created and not kept_existing_count and (skipped or conflicts):
            all_errs = conflicts + skipped
            raise UserError(_("No timetable slots were generated:\n%s") % "\n".join(all_errs[:10]))

        target_ids = created.ids or Slot.search([("section_id", "in", self.section_ids.ids)]).ids
        summary_title = _("Generated Timetable (Created: %d, Kept: %d, Holiday Skipped: %d)") % (
            len(created), kept_existing_count, holiday_skipped_count
        )

        return {
            "type": "ir.actions.act_window",
            "name": summary_title,
            "res_model": "university.timetable.slot",
            "view_mode": "gantt,list,form",
            "domain": [("id", "in", target_ids)],
            "context": {"default_mode": "week", "search_default_group_by_resource": 1},
        }
