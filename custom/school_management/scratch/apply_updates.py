import sys

def update_file(path, old_text, new_text):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_text not in content:
        raise ValueError(f"Old text not found in {path}:\n{old_text[:100]}...")
    content = content.replace(old_text, new_text, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print(f"Successfully updated {path}")

# ==========================================
# 1. Update models/student.py
# ==========================================
student_path = 'custom/school_management/models/student.py'

old_compute_curr = '''    @api.depends("program_id", "program_id.curriculum_line_ids", "curriculum_id", "curriculum_id.line_ids", "academic_year_id")
    def _compute_curriculum_line_ids(self):
        for student in self:
            if student.curriculum_id and student.curriculum_id.line_ids:
                student.curriculum_line_ids = student.curriculum_id.line_ids
            elif student.program_id:
                if student.academic_year_id:
                    session_curriculum = self.env["university.curriculum"].search([
                        ("program_id", "=", student.program_id.id),
                        ("session_id", "=", student.academic_year_id.id),
                    ], limit=1)
                    if session_curriculum and session_curriculum.line_ids:
                        student.curriculum_line_ids = session_curriculum.line_ids
                        continue
                if student.program_id.curriculum_line_ids:
                    student.curriculum_line_ids = student.program_id.curriculum_line_ids
                else:
                    student.curriculum_line_ids = False
            else:
                student.curriculum_line_ids = False'''

new_compute_curr = '''    @api.depends("program_id", "program_id.curriculum_line_ids", "curriculum_id", "curriculum_id.line_ids", "academic_year_id")
    def _compute_curriculum_line_ids(self):
        for student in self:
            curriculum = student.sudo().curriculum_id
            if curriculum and curriculum.line_ids:
                student.curriculum_line_ids = curriculum.line_ids
            elif student.program_id:
                if student.academic_year_id:
                    session_curriculum = self.env["university.curriculum"].sudo().search([
                        ("program_id", "=", student.program_id.id),
                        ("session_id", "=", student.academic_year_id.id),
                    ], limit=1)
                    if session_curriculum and session_curriculum.line_ids:
                        student.curriculum_line_ids = session_curriculum.line_ids
                        continue
                if student.program_id.sudo().curriculum_line_ids:
                    student.curriculum_line_ids = student.program_id.sudo().curriculum_line_ids
                else:
                    student.curriculum_line_ids = False
            else:
                student.curriculum_line_ids = False'''

update_file(student_path, old_compute_curr, new_compute_curr)

old_counts_def = '''    enrollment_count = fields.Integer(
        string="Enrollment Count",
        compute="_compute_counts",
        store=True,
    )
    submission_count = fields.Integer(
        string="Submission Count",
        compute="_compute_counts",
        store=True,
    )
    report_card_count = fields.Integer(
        string="Report Card Count",
        compute="_compute_counts",
        store=True,
    )'''

new_counts_def = '''    enrollment_count = fields.Integer(
        string="Enrollment Count",
        compute="_compute_counts",
    )
    session_count = fields.Integer(
        string="Total Sessions",
        compute="_compute_counts",
    )
    submission_count = fields.Integer(
        string="Submission Count",
        compute="_compute_counts",
    )
    report_card_count = fields.Integer(
        string="Report Card Count",
        compute="_compute_counts",
    )'''

update_file(student_path, old_counts_def, new_counts_def)

old_actions = '''    def action_view_enrollments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Enrollments - %s", self.name),
            "res_model": "university.enrollment",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    def action_view_fees(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fee Invoices - %s", self.name),
            "res_model": "university.fee",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    def action_view_submissions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Submissions - %s", self.name),
            "res_model": "university.assignment.submission",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }'''

new_actions = '''    def action_view_enrollments(self):
        self.ensure_one()
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        teacher_rec = False
        if not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        ):
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        domain = [("student_id", "=", self.id)]
        if teacher_rec:
            domain.append(("section_id.teacher_id", "=", teacher_rec.id))

        return {
            "type": "ir.actions.act_window",
            "name": _("Enrollments - %s", self.name),
            "res_model": "university.enrollment",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"default_student_id": self.id},
        }

    def action_view_sessions(self):
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
        }

    def action_view_fees(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fee Invoices - %s", self.name),
            "res_model": "university.fee",
            "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)],
            "context": {"default_student_id": self.id},
        }

    def action_view_submissions(self):
        self.ensure_one()
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        teacher_rec = False
        if not is_admin and (
            user.has_group("school_management.group_school_teacher")
            or user.has_group("school_management.group_university_teacher")
        ):
            teacher_rec = self.env["university.teacher"].search([("user_id", "=", user.id)], limit=1)

        domain = [("student_id", "=", self.id)]
        if teacher_rec:
            domain.append(("assignment_id.teacher_id", "=", teacher_rec.id))

        return {
            "type": "ir.actions.act_window",
            "name": _("Submissions - %s", self.name),
            "res_model": "university.assignment.submission",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"default_student_id": self.id},
        }'''

update_file(student_path, old_actions, new_actions)

old_compute_counts = '''    @api.depends("enrollment_ids", "submission_ids", "report_card_ids")
    def _compute_counts(self):
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
            self.env["university.report.card"]._read_group(
                [("student_id", "in", self.ids)],
                groupby=["student_id"],
                aggregates=["__count"],
            )
        )
        for student in self:
            student.enrollment_count = enrollment_data.get(student, 0)
            student.submission_count = submission_data.get(student, 0)
            student.report_card_count = report_card_data.get(student, 0)'''

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
                self.env["university.report.card"]._read_group(
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
                self.env["university.report.card"]._read_group(
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

update_file(student_path, old_compute_counts, new_compute_counts)

# ==========================================
# 2. Update security/record_rules.xml
# ==========================================
rr_path = 'custom/school_management/security/record_rules.xml'
old_rr = '''    <record id="rule_teacher_own_section_students" model="ir.rule">
        <field name="name">Teacher: students in own sections or advisees</field>
        <field name="model_id" ref="model_university_student"/>
        <field name="groups" eval="[(4, ref('group_university_teacher'))]"/>
        <field name="domain_force">[('enrollment_ids.section_id.teacher_id.user_id', '=', user.id)]</field>'''

new_rr = '''    <record id="rule_teacher_own_section_students" model="ir.rule">
        <field name="name">Teacher: students in own sections or advisees</field>
        <field name="model_id" ref="model_university_student"/>
        <field name="groups" eval="[(4, ref('group_university_teacher'))]"/>
        <field name="domain_force">['|', ('advisor_id.user_id', '=', user.id), ('enrollment_ids.section_id.teacher_id.user_id', '=', user.id)]</field>'''

update_file(rr_path, old_rr, new_rr)

# ==========================================
# 3. Update security/security.xml
# ==========================================
sec_path = 'custom/school_management/security/security.xml'
old_sec = '''    <record id="rule_teacher_ui_students" model="ir.rule">
        <field name="name">Teacher: students in assigned sections</field>
        <field name="model_id" ref="model_university_student"/>
        <field name="domain_force">[('enrollment_ids.section_id.teacher_id.user_id', '=', user.id)]</field>'''

new_sec = '''    <record id="rule_teacher_ui_students" model="ir.rule">
        <field name="name">Teacher: students in assigned sections</field>
        <field name="model_id" ref="model_university_student"/>
        <field name="domain_force">['|', ('advisor_id.user_id', '=', user.id), ('enrollment_ids.section_id.teacher_id.user_id', '=', user.id)]</field>'''

update_file(sec_path, old_sec, new_sec)

# ==========================================
# 4. Update views/student_views.xml
# ==========================================
sv_path = 'custom/school_management/views/student_views.xml'

# In list view: add session_count
old_list = '''                <field name="enrollment_count" string="Classes" optional="show"/>'''
new_list = '''                <field name="enrollment_count" string="Classes" optional="show"/>
                <field name="session_count" string="Sessions" optional="show"/>'''
update_file(sv_path, old_list, new_list)

# In kanban fields: add session_count
old_kanban_fields = '''                <field name="academic_year_id"/>
                <field name="enrollment_count"/>
                <field name="email"/>'''
new_kanban_fields = '''                <field name="academic_year_id"/>
                <field name="enrollment_count"/>
                <field name="session_count"/>
                <field name="email"/>'''
update_file(sv_path, old_kanban_fields, new_kanban_fields)

# In kanban footer: show classes & sessions
old_kanban_footer = '''                        <!-- Footer: enrolled classes chip and email widget -->
                        <footer class="d-flex align-items-center justify-content-between pt-2 mt-2 border-top">
                            <span class="badge text-bg-light border text-muted small" title="Enrolled Classes">
                                <i class="fa fa-book me-1"/>
                                <t t-out="record.enrollment_count.raw_value"/> Classes
                            </span>
                            <div class="text-truncate small ms-2">
                                <field name="email" widget="email"/>
                            </div>
                        </footer>'''

new_kanban_footer = '''                        <!-- Footer: enrolled classes chip, sessions chip, and email widget -->
                        <footer class="d-flex align-items-center justify-content-between pt-2 mt-2 border-top">
                            <div class="d-flex align-items-center gap-1">
                                <span class="badge text-bg-light border text-muted small" title="Enrolled Classes">
                                    <i class="fa fa-book me-1"/>
                                    <t t-out="record.enrollment_count.raw_value"/> Classes
                                </span>
                                <span class="badge text-bg-light border text-muted small" title="Total Sessions">
                                    <i class="fa fa-calendar me-1"/>
                                    <t t-out="record.session_count.raw_value"/> Sessions
                                </span>
                            </div>
                            <div class="text-truncate small ms-2">
                                <field name="email" widget="email"/>
                            </div>
                        </footer>'''
update_file(sv_path, old_kanban_footer, new_kanban_footer)

# In form view: stat button for sessions
old_form_stat = '''                        <button name="action_view_enrollments" type="object" class="oe_stat_button" icon="fa-graduation-cap">
                            <field name="enrollment_count" widget="statinfo" string="Enrollments"/>
                        </button>
                        <button name="action_view_exam_scores"'''

new_form_stat = '''                        <button name="action_view_enrollments" type="object" class="oe_stat_button" icon="fa-graduation-cap">
                            <field name="enrollment_count" widget="statinfo" string="Enrollments"/>
                        </button>
                        <button name="action_view_sessions" type="object" class="oe_stat_button" icon="fa-calendar">
                            <field name="session_count" widget="statinfo" string="Sessions"/>
                        </button>
                        <button name="action_view_exam_scores"'''
update_file(sv_path, old_form_stat, new_form_stat)

# In my_curriculum_tab: replace parent.year_level
old_curr_tab = '''                        <page string="My Curriculum" name="my_curriculum_tab">
                            <field name="curriculum_line_ids" readonly="1" context="{'active_student_id': id}">
                                <list limit="10" default_order="year_level, semester_number, sequence, id"
                                      decoration-bf="year_level == parent.year_level"
                                      decoration-info="year_level == parent.year_level">
                                    <field name="subject_id"/>
                                    <field name="year_level"/>
                                    <field name="semester_number"/>
                                    <field name="credits" sum="Total Credits"/>
                                    <field name="is_student_enrolled" column_invisible="1"/>
                                    <field name="enrollment_status" string="Status" widget="badge"'''

new_curr_tab = '''                        <page string="My Curriculum" name="my_curriculum_tab">
                            <field name="curriculum_line_ids" readonly="1" context="{'active_student_id': id}">
                                <list limit="10" default_order="year_level, semester_number, sequence, id"
                                      decoration-bf="is_current_student_year"
                                      decoration-info="is_current_student_year">
                                    <field name="subject_id"/>
                                    <field name="year_level"/>
                                    <field name="semester_number"/>
                                    <field name="credits" sum="Total Credits"/>
                                    <field name="is_student_enrolled" column_invisible="1"/>
                                    <field name="is_current_student_year" column_invisible="1"/>
                                    <field name="enrollment_status" string="Status" widget="badge"'''
update_file(sv_path, old_curr_tab, new_curr_tab)

# ==========================================
# 5. Update views/timetable_views.xml
# ==========================================
tv_path = 'custom/school_management/views/timetable_views.xml'
old_tv = '''                <filter string="This Week" name="filter_this_week"
                        domain="[('session_date', '&gt;=', context_today() - relativedelta(days=context_today().weekday())), ('session_date', '&lt;', context_today() - relativedelta(days=context_today().weekday()) + relativedelta(days=7))]"/>'''

new_tv = '''                <filter string="This Week" name="filter_this_week" domain="[('is_this_week', '=', True)]"/>'''
update_file(tv_path, old_tv, new_tv)

# ==========================================
# 6. Update models/assignment.py & views/assignment_views.xml
# ==========================================
as_path = 'custom/school_management/models/assignment.py'
old_as_import = '''from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError'''

new_as_import = '''from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError'''
update_file(as_path, old_as_import, new_as_import)

old_as_field = '''    max_score = fields.Float(string="Max Score", default=100.0)'''
new_as_field = '''    max_score = fields.Float(string="Max Score", default=100.0)
    is_due_this_week = fields.Boolean(
        string="Due This Week",
        compute="_compute_is_due_this_week",
        search="_search_is_due_this_week",
    )'''
update_file(as_path, old_as_field, new_as_field)

old_as_method = '''    @api.depends("submission_ids")
    def _compute_submission_count(self):'''

new_as_method = '''    @api.depends("due_date")
    def _compute_is_due_this_week(self):
        today = fields.Date.context_today(self)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        for rec in self:
            rec.is_due_this_week = bool(rec.due_date and monday <= rec.due_date <= sunday)

    def _search_is_due_this_week(self, operator, value):
        if operator not in ("=", "!="):
            return []
        today = fields.Date.context_today(self)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        matching_domain = [("due_date", ">=", monday), ("due_date", "<=", sunday)]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return matching_domain
        return ["|", ("due_date", "<", monday), ("due_date", ">", sunday)]

    @api.depends("submission_ids")
    def _compute_submission_count(self):'''
update_file(as_path, old_as_method, new_as_method)

av_path = 'custom/school_management/views/assignment_views.xml'
old_av = '''                <filter string="Due This Week" name="due_this_week"
                        domain="[('due_date', '>=', context_today() - relativedelta(days=context_today().weekday())), ('due_date', '&lt;', context_today() - relativedelta(days=context_today().weekday()) + relativedelta(days=7))]"/>'''

new_av = '''                <filter string="Due This Week" name="due_this_week" domain="[('is_due_this_week', '=', True)]"/>'''
update_file(av_path, old_av, new_av)

print("All updates applied cleanly!")
