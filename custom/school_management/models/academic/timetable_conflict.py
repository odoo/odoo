from odoo import _, api, fields, models


class UniversityTimetableConflict(models.Model):
    _name = "university.timetable.conflict"
    _description = "Schedule Conflict"
    _order = "severity asc, date asc, start_time asc"

    name = fields.Char(string="Conflict Title", required=True)
    conflict_type = fields.Selection(
        [
            ("teacher", "Teacher Conflict"),
            ("classroom", "Classroom Conflict"),
            ("timeslot", "Timeslot Conflict"),
            ("duplicate", "Duplicate Class Schedule"),
            ("capacity", "Classroom Capacity Problem"),
            ("holiday", "Holiday Conflict"),
        ],
        string="Conflict Type",
        required=True,
    )
    severity = fields.Selection(
        [
            ("danger", "Critical Overlap"),
            ("warning", "Warning"),
        ],
        string="Severity",
        default="danger",
        required=True,
    )
    academic_year_id = fields.Many2one("university.academic.year", string="Academic Year")
    semester_id = fields.Many2one("university.semester", string="Academic Term / Semester")
    date = fields.Date(string="Date")
    start_time = fields.Datetime(string="Start Time")
    end_time = fields.Datetime(string="End Time")
    time_range = fields.Char(string="Time Range")
    teacher_id = fields.Many2one("university.teacher", string="Teacher")
    classroom_id = fields.Many2one("university.classroom", string="Classroom")
    section_id = fields.Many2one("university.class.section", string="Class Section")
    holiday_id = fields.Many2one("university.holiday", string="Holiday")
    slot_ids = fields.Many2many(
        "university.timetable.slot",
        "university_timetable_conflict_slot_rel",
        "conflict_id",
        "slot_id",
        string="Conflicting Sessions",
    )
    description = fields.Text(string="Description / Details", required=True)
    status = fields.Selection(
        [
            ("unresolved", "Unresolved"),
            ("resolved", "Resolved"),
        ],
        string="Status",
        default="unresolved",
    )

    @api.model
    def action_open_conflicts_view(self, academic_year_id=None):
        """Scan active slots and open the Schedule Conflicts page."""
        self._detect_all_conflicts(academic_year_id=academic_year_id)
        ctx = {"search_default_filter_unresolved": 1}
        domain = []
        if academic_year_id:
            domain.append(("academic_year_id", "=", academic_year_id))
            ctx["default_academic_year_id"] = academic_year_id
        return {
            "name": _("Schedule Conflicts"),
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.conflict",
            "view_mode": "kanban,list,form",
            "domain": domain,
            "limit": 10,
            "search_view_id": self.env.ref("school_management.view_university_timetable_conflict_search").id,
            "context": ctx,
        }

    def action_rescan(self):
        ay_id = self.mapped("academic_year_id.id")
        ay_id = ay_id[0] if len(ay_id) == 1 else None
        sem_id = self.mapped("semester_id.id")
        sem_id = sem_id[0] if len(sem_id) == 1 else None
        self._detect_all_conflicts(semester_id=sem_id, academic_year_id=ay_id)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Conflict Scan Complete"),
                "message": _("All schedule conflicts have been refreshed."),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def action_view_slots(self):
        self.ensure_one()
        return {
            "name": _("Conflicting Timetable Slots"),
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.slot",
            "view_mode": "list,form,calendar",
            "domain": [("id", "in", self.slot_ids.ids)],
            "target": "current",
        }

    def action_mark_resolved(self):
        self.write({"status": "resolved"})
        return True

    @api.model
    def _detect_all_conflicts(self, semester_id=None, academic_year_id=None):
        """Scan active timetable slots and detect scheduling clashes."""
        domain = [("state", "!=", "cancelled")]
        if semester_id:
            domain.append(("semester_id", "=", semester_id))
        if academic_year_id:
            domain.append(("academic_year_id", "=", academic_year_id))

        slots = self.env["university.timetable.slot"].search(domain, order="start_time asc")

        # Clear existing unresolved conflicts for this scope to avoid duplicates
        clear_domain = [("status", "=", "unresolved")]
        if semester_id:
            clear_domain.append(("semester_id", "=", semester_id))
        if academic_year_id:
            clear_domain.append(("academic_year_id", "=", academic_year_id))
        self.search(clear_domain).unlink()

        conflicts_to_create = []
        seen_pairs = set()

        # 1. Overlapping pairs (Teacher, Classroom, Duplicate Section, Timeslot)
        for i, s1 in enumerate(slots):
            if not s1.start_time or not s1.end_time:
                continue
            for s2 in slots[i + 1:]:
                if not s2.start_time or not s2.end_time:
                    continue
                if s1.start_time < s2.end_time and s1.end_time > s2.start_time:
                    pair_teacher = ("teacher", min(s1.id, s2.id), max(s1.id, s2.id))
                    pair_room = ("room", min(s1.id, s2.id), max(s1.id, s2.id))
                    pair_sec = ("section", min(s1.id, s2.id), max(s1.id, s2.id))
                    pair_timeslot = ("timeslot", min(s1.id, s2.id), max(s1.id, s2.id))

                    s1_start = fields.Datetime.context_timestamp(s1, s1.start_time)
                    s1_end = fields.Datetime.context_timestamp(s1, s1.end_time)
                    time_range = f"{s1_start.strftime('%A %H:%M')} - {s1_end.strftime('%H:%M')}"

                    # Teacher Conflict
                    if s1.teacher_id and s2.teacher_id and s1.teacher_id == s2.teacher_id and pair_teacher not in seen_pairs:
                        seen_pairs.add(pair_teacher)
                        conflicts_to_create.append({
                            "name": _("Teacher Conflict: %s") % s1.teacher_id.name,
                            "conflict_type": "teacher",
                            "severity": "danger",
                            "academic_year_id": s1.academic_year_id.id if s1.academic_year_id else False,
                            "semester_id": s1.semester_id.id if s1.semester_id else False,
                            "date": s1_start.date(),
                            "start_time": s1.start_time,
                            "end_time": max(s1.end_time, s2.end_time),
                            "time_range": time_range,
                            "teacher_id": s1.teacher_id.id,
                            "section_id": s1.section_id.id,
                            "classroom_id": s1.classroom_id.id if s1.classroom_id else False,
                            "slot_ids": [(6, 0, [s1.id, s2.id])],
                            "description": _("Teacher %s is assigned to multiple classes at the same time: '%s' and '%s'.") % (
                                s1.teacher_id.name,
                                s1.name or s1.subject_id.name,
                                s2.name or s2.subject_id.name,
                            ),
                        })

                    # Classroom Conflict
                    if s1.classroom_id and s2.classroom_id and s1.classroom_id == s2.classroom_id and pair_room not in seen_pairs:
                        seen_pairs.add(pair_room)
                        conflicts_to_create.append({
                            "name": _("Classroom Conflict: %s") % s1.classroom_id.name,
                            "conflict_type": "classroom",
                            "severity": "danger",
                            "academic_year_id": s1.academic_year_id.id if s1.academic_year_id else False,
                            "semester_id": s1.semester_id.id if s1.semester_id else False,
                            "date": s1_start.date(),
                            "start_time": s1.start_time,
                            "end_time": max(s1.end_time, s2.end_time),
                            "time_range": time_range,
                            "classroom_id": s1.classroom_id.id,
                            "section_id": s1.section_id.id,
                            "teacher_id": s1.teacher_id.id if s1.teacher_id else False,
                            "slot_ids": [(6, 0, [s1.id, s2.id])],
                            "description": _("Classroom %s is double-booked by '%s' and '%s' during this timeslot.") % (
                                s1.classroom_id.name,
                                s1.name or s1.subject_id.name,
                                s2.name or s2.subject_id.name,
                            ),
                        })

                    # Duplicate Class Schedule
                    if s1.section_id and s2.section_id and s1.section_id == s2.section_id and pair_sec not in seen_pairs:
                        seen_pairs.add(pair_sec)
                        conflicts_to_create.append({
                            "name": _("Duplicate Class Schedule: %s") % s1.section_id.name,
                            "conflict_type": "duplicate",
                            "severity": "danger",
                            "academic_year_id": s1.academic_year_id.id if s1.academic_year_id else False,
                            "semester_id": s1.semester_id.id if s1.semester_id else False,
                            "date": s1_start.date(),
                            "start_time": s1.start_time,
                            "end_time": max(s1.end_time, s2.end_time),
                            "time_range": time_range,
                            "section_id": s1.section_id.id,
                            "teacher_id": s1.teacher_id.id if s1.teacher_id else False,
                            "classroom_id": s1.classroom_id.id if s1.classroom_id else False,
                            "slot_ids": [(6, 0, [s1.id, s2.id])],
                            "description": _("Class section '%s' has duplicate concurrent sessions: '%s' and '%s'.") % (
                                s1.section_id.name,
                                s1.subject_id.name if s1.subject_id else s1.name,
                                s2.subject_id.name if s2.subject_id else s2.name,
                            ),
                        })

                    # Timeslot Conflict (same timeslot reference clashed)
                    if s1.timeslot_id and s2.timeslot_id and s1.timeslot_id == s2.timeslot_id and pair_timeslot not in seen_pairs:
                        if (s1.teacher_id == s2.teacher_id) or (s1.classroom_id == s2.classroom_id) or (s1.section_id == s2.section_id):
                            seen_pairs.add(pair_timeslot)
                            conflicts_to_create.append({
                                "name": _("Timeslot Clash: %s") % s1.timeslot_id.name,
                                "conflict_type": "timeslot",
                                "severity": "danger",
                                "academic_year_id": s1.academic_year_id.id if s1.academic_year_id else False,
                                "semester_id": s1.semester_id.id if s1.semester_id else False,
                                "date": s1_start.date(),
                                "start_time": s1.start_time,
                                "end_time": max(s1.end_time, s2.end_time),
                                "time_range": time_range,
                                "section_id": s1.section_id.id,
                                "teacher_id": s1.teacher_id.id if s1.teacher_id else False,
                                "classroom_id": s1.classroom_id.id if s1.classroom_id else False,
                                "slot_ids": [(6, 0, [s1.id, s2.id])],
                                "description": _("Timeslot '%s' has conflicting scheduled classes.") % (
                                    s1.timeslot_id.name,
                                ),
                            })

        # 2. Classroom Capacity Problem
        seen_capacity_slots = set()
        for s in slots:
            if s.classroom_id and s.classroom_id.capacity > 0:
                enrolled = s.enrolled_student_count or 0
                cap = s.classroom_id.capacity
                if enrolled > cap and s.id not in seen_capacity_slots:
                    seen_capacity_slots.add(s.id)
                    s_start = fields.Datetime.context_timestamp(s, s.start_time) if s.start_time else False
                    conflicts_to_create.append({
                        "name": _("Capacity Problem: %s in %s") % (s.section_id.name, s.classroom_id.name),
                        "conflict_type": "capacity",
                        "severity": "warning",
                        "academic_year_id": s.academic_year_id.id if s.academic_year_id else False,
                        "semester_id": s.semester_id.id if s.semester_id else False,
                        "date": s_start.date() if s_start else False,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "time_range": f"{s_start.strftime('%A %H:%M')} - {fields.Datetime.context_timestamp(s, s.end_time).strftime('%H:%M')}" if s_start and s.end_time else "",
                        "classroom_id": s.classroom_id.id,
                        "section_id": s.section_id.id,
                        "teacher_id": s.teacher_id.id if s.teacher_id else False,
                        "slot_ids": [(6, 0, [s.id])],
                        "description": _("Enrolled student count (%d) exceeds room capacity (%d) of classroom '%s'.") % (
                            enrolled,
                            cap,
                            s.classroom_id.name,
                        ),
                    })

        # 3. Holiday Conflict
        holidays = self.env["university.holiday"].sudo().search([])
        seen_holiday_slots = set()
        for s in slots:
            if not s.start_time or s.id in seen_holiday_slots:
                continue
            slot_date = fields.Datetime.context_timestamp(s, s.start_time).date()
            faculty = (
                s.section_id.program_id.department_id.faculty_id
                if s.section_id.program_id and s.section_id.program_id.department_id
                else False
            )
            for h in holidays:
                if h.date_start <= slot_date <= h.date_end:
                    if not h.faculty_id or (faculty and h.faculty_id == faculty):
                        seen_holiday_slots.add(s.id)
                        s_start = fields.Datetime.context_timestamp(s, s.start_time)
                        conflicts_to_create.append({
                            "name": _("Holiday Conflict: %s on %s") % (s.name or s.section_id.name, h.name),
                            "conflict_type": "holiday",
                            "severity": "warning",
                            "academic_year_id": s.academic_year_id.id if s.academic_year_id else False,
                            "semester_id": s.semester_id.id if s.semester_id else False,
                            "date": slot_date,
                            "start_time": s.start_time,
                            "end_time": s.end_time,
                            "time_range": f"{s_start.strftime('%A %H:%M')} - {fields.Datetime.context_timestamp(s, s.end_time).strftime('%H:%M')}",
                            "holiday_id": h.id,
                            "section_id": s.section_id.id,
                            "teacher_id": s.teacher_id.id if s.teacher_id else False,
                            "classroom_id": s.classroom_id.id if s.classroom_id else False,
                            "slot_ids": [(6, 0, [s.id])],
                            "description": _("Session '%s' is scheduled on %s, which is university holiday '%s'.") % (
                                s.name or s.section_id.name,
                                slot_date,
                                h.name,
                            ),
                        })
                        break

        if conflicts_to_create:
            self.create(conflicts_to_create)
        return len(conflicts_to_create)
