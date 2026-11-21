with open('custom/school_management/models/exam.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_inherit = '_inherit = ["mail.thread", "mail.activity.mixin"]\n    _order = "exam_date desc, id desc"'
new_inherit = '''_inherit = ["mail.thread", "mail.activity.mixin", "university.document.download.mixin"]
    _order = "exam_date desc, id desc"

    _download_report_xmlid = "school_management.action_report_university_exam_marksheet"'''

old_actions = """    def action_download_marksheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/xlsx',
            'target': 'self',
        }

    def action_print_marksheet_pdf(self):
        self.ensure_one()
        return self.env.ref("school_management.action_report_university_exam_marksheet").report_action(self)

    def action_download_marksheet_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/pdf',
            'target': 'self',
        }"""

new_actions = """    def _generate_xlsx_bytes(self):
        self.ensure_one()
        from ..controllers.exam_marksheet import build_marksheet_xlsx
        exam_type_label = dict(self._fields['exam_type'].selection).get(self.exam_type, (self.exam_type or 'Exam').capitalize())
        state_label = dict(self._fields['state'].selection).get(self.state, (self.state or '').capitalize())
        course_label = f"[{self.subject_id.code}] {self.subject_id.name}" if self.subject_id.code else (self.subject_id.name or 'Subject')
        period_label = f"{self.academic_year_id.name or ''} - {self.semester_id.name or ''}".strip(' -')
        teacher_label = f"{self.teacher_id.name} ({self.teacher_id.teacher_id})" if self.teacher_id.teacher_id else (self.teacher_id.name or 'Course Instructor')
        duration_str = f"{self.duration_minutes} minutes" if self.duration_minutes else 'Standard Duration'
        date_str = str(self.exam_date) if self.exam_date else 'TBA'
        date_duration_label = f"{date_str} ({duration_str})"

        exam_info = {
            'institution': self.env.company.name or 'HARVARD UNIVERSITY - FACULTY ACADEMIC PORTAL',
            'course': course_label,
            'section': self.section_id.name or 'N/A',
            'program': self.program_id.name or (self.section_id.program_id.name if self.section_id else 'N/A'),
            'department': self.department_id.name or (self.section_id.department_id.name if self.section_id else 'Academic Department'),
            'academic_period': period_label,
            'teacher': teacher_label,
            'teacher_name': self.teacher_id.name or 'Teacher',
            'teacher_code': self.teacher_id.teacher_id or '',
            'weight': f"{self.weight_percent:.1f}%" if self.weight_percent else 'N/A',
            'exam_type': exam_type_label,
            'exam_date_duration': date_duration_label,
            'status': state_label,
            'avg_score': self.average_score or 0.0,
            'pass_count': self.pass_count or 0,
            'fail_count': self.fail_count or 0,
            'student_count': self.student_count or len(self.score_ids),
        }

        subjects = [self.subject_id.name or 'Subject']
        students = []
        for score in self.score_ids.sorted(key=lambda s: (s.student_code or '', s.student_id.name or '')):
            students.append({
                'id': score.student_code or score.student_id.student_id or f'STU-{score.student_id.id}',
                'name': score.student_id.name or '',
                'is_absent': score.is_absent,
                'raw_score': score.score,
                'penalty': score.penalty_applied or 0.0,
                'final_score': score.final_score if not score.is_absent else 0.0,
                'percentage': score.percentage or 0.0,
                'remark': score.remark or '',
                'marks': [score.final_score if not score.is_absent else 0.0],
            })

        full_marks = self.max_score or 100.0
        pass_marks = round(full_marks * 0.5, 2)

        return build_marksheet_xlsx(
            title=self.name or 'Student Examination Marksheet',
            subtitle=f"{exam_type_label} Official Ledger",
            full_marks=full_marks,
            pass_marks=pass_marks,
            subjects=subjects,
            students=students,
            exam_info=exam_info,
        )

    def _get_xlsx_data(self):
        self.ensure_one()
        headers = ["No.", "Student ID", "Student Name", "Attendance", "Raw Score", "Final Score", "Percentage", "Result"]
        rows = []
        for idx, score in enumerate(self.score_ids.sorted(key=lambda s: (s.student_code or '', s.student_id.name or '')), 1):
            rows.append([
                idx,
                score.student_code or score.student_id.student_id or '',
                score.student_id.name or '',
                'Absent' if score.is_absent else 'Present',
                score.score if not score.is_absent else 0.0,
                score.final_score if not score.is_absent else 0.0,
                f"{score.percentage:.1f}%",
                'ABSENT' if score.is_absent else ('PASS' if score.is_passed else 'FAIL'),
            ])
        return (f"Exam_{self.id}", headers, rows)

    def action_download_marksheet(self):
        self.ensure_one()
        if hasattr(self, '_log_download'):
            self._log_download(file_type='Excel')
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/xlsx',
            'target': 'self',
        }

    def action_print_marksheet_pdf(self):
        self.ensure_one()
        if hasattr(self, '_log_download'):
            self._log_download(file_type='PDF')
        return self.env.ref("school_management.action_report_university_exam_marksheet").report_action(self)

    def action_download_marksheet_pdf(self):
        self.ensure_one()
        if hasattr(self, '_log_download'):
            self._log_download(file_type='PDF')
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/marksheet/{self.id}/pdf',
            'target': 'self',
        }"""

assert old_inherit in text, "old_inherit not found!"
assert old_actions in text, "old_actions not found!"

text = text.replace(old_inherit, new_inherit, 1)
text = text.replace(old_actions, new_actions, 1)

with open('custom/school_management/models/exam.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patch applied successfully.")
