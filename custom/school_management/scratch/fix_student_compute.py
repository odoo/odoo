with open('custom/school_management/models/student.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_actions_block = '''    def action_view_sessions(self):
        self.ensure_one()
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        teacher_rec = False
        if not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        ):
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        if teacher_rec:
            sec_ids = self.enrollment_ids.filtered(lambda e: e.section_id.teacher_id == teacher_rec).mapped("section_id").ids
            domain = [("section_id", "in", sec_ids), "|", ("teacher_id", "=", teacher_rec.id), ("instructor_id", "=", teacher_rec.id)]
        else:
            sec_ids = self.enrollment_ids.mapped("section_id").ids
            domain = [("section_id", "in", sec_ids)]

        return {
            "type": "ir.actions.act_window",
            "name": _("Sessions - %s", self.name),
            "res_model": "university.timetable.slot",
            "view_mode": "calendar,list,form",
            "domain": domain,
            "context": {"default_student_id": self.id},
        }'''

new_actions_block = '''    def action_view_sessions(self):
        self.ensure_one()
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        teacher_rec = False
        if not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        ):
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        if teacher_rec:
            teacher_enrs = self.sudo().enrollment_ids.filtered(lambda e: e.section_id.teacher_id == teacher_rec)
            sec_ids = teacher_enrs.mapped("section_id").ids
            domain = [("section_id", "in", sec_ids), "|", ("teacher_id", "=", teacher_rec.id), ("instructor_id", "=", teacher_rec.id)]
        else:
            sec_ids = self.sudo().enrollment_ids.mapped("section_id").ids
            domain = [("section_id", "in", sec_ids)]

        return {
            "type": "ir.actions.act_window",
            "name": _("Sessions - %s", self.name),
            "res_model": "university.timetable.slot",
            "view_mode": "calendar,list,form",
            "domain": domain,
            "context": {"default_student_id": self.id},
        }'''

assert old_actions_block in text, "old_actions_block not found"
text = text.replace(old_actions_block, new_actions_block, 1)

old_compute_counts = '''    @api.depends("enrollment_ids", "submission_ids", "report_card_ids")
    @api.depends_context("uid")
    def _compute_counts(self):
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        is_teacher = not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        )
        teacher_rec = False
        if is_teacher:
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        if teacher_rec:
            enrollment_data = dict(
                self.env["university.enrollment"]._read_group(
                    [("student_id", "in", self.ids), ("section_id.teacher_id", "=", teacher_rec.id)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            submission_data = dict(
                self.env["university.assignment.submission"]._read_group(
                    [("student_id", "in", self.ids), ("assignment_id.teacher_id", "=", teacher_rec.id)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            report_card_data = dict(
                self.env["university.report.card"].sudo()._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            teacher_slots = self.env["university.timetable.slot"].search([
                "|",
                ("teacher_id", "=", teacher_rec.id),
                ("instructor_id", "=", teacher_rec.id),
            ])
            sec_slot_map = {}
            for slot in teacher_slots:
                if slot.section_id:
                    sec_slot_map[slot.section_id.id] = sec_slot_map.get(slot.section_id.id, 0) + 1

            for student in self:
                student.enrollment_count = enrollment_data.get(student, 0)
                student.submission_count = submission_data.get(student, 0)
                student.report_card_count = report_card_data.get(student, 0)
                teacher_sections = student.enrollment_ids.filtered(
                    lambda e: e.section_id.teacher_id == teacher_rec
                ).mapped("section_id")
                student.session_count = sum(sec_slot_map.get(s.id, 0) for s in teacher_sections)
        else:
            enrollment_data = dict(
                self.env["university.enrollment"]._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            submission_data = dict(
                self.env["university.assignment.submission"]._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            report_card_data = dict(
                self.env["university.report.card"].sudo()._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            all_slots = self.env["university.timetable.slot"].search([
                ("section_id", "!=", False)
            ])
            sec_slot_map = {}
            for slot in all_slots:
                sec_slot_map[slot.section_id.id] = sec_slot_map.get(slot.section_id.id, 0) + 1

            for student in self:
                student.enrollment_count = enrollment_data.get(student, 0)
                student.submission_count = submission_data.get(student, 0)
                student.report_card_count = report_card_data.get(student, 0)
                student_sections = student.enrollment_ids.mapped("section_id")
                student.session_count = sum(sec_slot_map.get(s.id, 0) for s in student_sections)'''

new_compute_counts = '''    @api.depends("enrollment_ids", "submission_ids", "report_card_ids")
    @api.depends_context("uid")
    def _compute_counts(self):
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        is_teacher = not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        )
        teacher_rec = False
        if is_teacher:
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        if teacher_rec:
            enrollment_data = dict(
                self.env["university.enrollment"].sudo()._read_group(
                    [("student_id", "in", self.ids), ("section_id.teacher_id", "=", teacher_rec.id)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            submission_data = dict(
                self.env["university.assignment.submission"].sudo()._read_group(
                    [("student_id", "in", self.ids), ("assignment_id.teacher_id", "=", teacher_rec.id)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            report_card_data = dict(
                self.env["university.report.card"].sudo()._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            teacher_slots = self.env["university.timetable.slot"].sudo().search([
                "|",
                ("teacher_id", "=", teacher_rec.id),
                ("instructor_id", "=", teacher_rec.id),
            ])
            sec_slot_map = {}
            for slot in teacher_slots:
                if slot.section_id:
                    sec_slot_map[slot.section_id.id] = sec_slot_map.get(slot.section_id.id, 0) + 1

            teacher_enrollments = self.env["university.enrollment"].sudo().search([
                ("student_id", "in", self.ids),
                ("section_id.teacher_id", "=", teacher_rec.id),
            ])
            student_sec_map = {}
            for enr in teacher_enrollments:
                if enr.section_id:
                    student_sec_map.setdefault(enr.student_id.id, []).append(enr.section_id.id)

            for student in self:
                student.enrollment_count = enrollment_data.get(student, 0)
                student.submission_count = submission_data.get(student, 0)
                student.report_card_count = report_card_data.get(student, 0)
                sec_ids = student_sec_map.get(student.id, [])
                student.session_count = sum(sec_slot_map.get(s, 0) for s in sec_ids)
        else:
            enrollment_data = dict(
                self.env["university.enrollment"]._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            submission_data = dict(
                self.env["university.assignment.submission"]._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            report_card_data = dict(
                self.env["university.report.card"].sudo()._read_group(
                    [("student_id", "in", self.ids)],
                    groupby=["student_id"],
                    aggregates=["__count"],
                )
            )
            all_slots = self.env["university.timetable.slot"].search([
                ("section_id", "!=", False)
            ])
            sec_slot_map = {}
            for slot in all_slots:
                sec_slot_map[slot.section_id.id] = sec_slot_map.get(slot.section_id.id, 0) + 1

            all_enrollments = self.env["university.enrollment"].sudo().search([
                ("student_id", "in", self.ids),
            ])
            student_sec_map = {}
            for enr in all_enrollments:
                if enr.section_id:
                    student_sec_map.setdefault(enr.student_id.id, []).append(enr.section_id.id)

            for student in self:
                student.enrollment_count = enrollment_data.get(student, 0)
                student.submission_count = submission_data.get(student, 0)
                student.report_card_count = report_card_data.get(student, 0)
                sec_ids = student_sec_map.get(student.id, [])
                student.session_count = sum(sec_slot_map.get(s, 0) for s in sec_ids)'''

assert old_compute_counts in text, "old_compute_counts not found"
text = text.replace(old_compute_counts, new_compute_counts, 1)

with open('custom/school_management/models/student.py', 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("fix_student_compute.py applied successfully!")
