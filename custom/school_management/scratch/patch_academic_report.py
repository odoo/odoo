path = r"custom\school_management\reports\academic_report.py"

content = '''from odoo import api, fields, models


class AcademicTranscriptReport(models.AbstractModel):
    _name = "report.school_management.report_university_transcript_document"
    _description = "Academic Transcript Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["university.transcript"].browse(docids)
        first = docs[:1]
        today = fields.Date.context_today(self)

        scale = first.grade_scale_id
        if not scale:
            scale = self.env["university.report.card"].search(
                [
                    ("student_id", "=", first.student_id.id),
                    ("state", "in", ["generated", "approved"]),
                ],
                order="id desc",
                limit=1,
            ).grade_scale_id
        if not scale:
            scale = self.env["university.grade.scale"].search([], order="id", limit=1)

        grade_lines = (
            scale.line_ids.sorted("min_score", reverse=True)
            if scale
            else self.env["university.grade.scale.line"]
        )
        has_honors = bool(
            grade_lines
            and "honors_grade_point" in grade_lines._fields
            and any(line.honors_grade_point > 0 for line in grade_lines)
        )
        if has_honors:
            weighted_max = max(line.honors_grade_point for line in grade_lines if line.honors_grade_point > 0)
        else:
            weighted_max = 4.0

        unweighted_values = [line.grade_point for line in grade_lines] if grade_lines else []
        unweighted_max = max(unweighted_values) if unweighted_values else 4.0

        # Course Repeat / Retake Policy:
        # Group lines by subject_id. If a subject is attempted more than once, only the
        # attempt with the highest grade_point (or latest attempt if tied) counts toward
        # cumulative credits and cumulative GPA.
        subject_lines = {}
        for line in first.line_ids:
            subject_lines.setdefault(line.subject_id.id, []).append(line)

        best_line_ids = set()
        repeated_line_ids = set()
        for sub_id, attempts in subject_lines.items():
            if len(attempts) == 1:
                best_line_ids.add(attempts[0].id)
            else:
                sorted_attempts = sorted(
                    attempts,
                    key=lambda l: (
                        l.grade_point or 0.0,
                        l.academic_year_id.date_start or fields.Date.min,
                        l.semester_id.date_start or fields.Date.min,
                        l.id or 0,
                    ),
                    reverse=True,
                )
                best_line_ids.add(sorted_attempts[0].id)
                for rep in sorted_attempts[1:]:
                    repeated_line_ids.add(rep.id)

        effective_lines = [l for l in first.line_ids if l.id in best_line_ids]
        total_credits = sum(l.credits for l in effective_lines if l.is_passing or (l.grade_point or 0.0) > 0)
        gpa_credits = sum(l.credits for l in effective_lines)
        unweighted_quality = sum(l.credits * (l.grade_point or 0.0) for l in effective_lines)
        unweighted_gpa = (unweighted_quality / gpa_credits) if gpa_credits else 0.0

        honors_by_grade = {
            line.name: line.honors_grade_point for line in grade_lines
        } if has_honors else {}

        honors_quality = sum(
            l.credits * honors_by_grade.get(l.grade, l.grade_point or 0.0)
            for l in effective_lines
        )
        weighted_gpa = (
            honors_quality / gpa_credits
            if has_honors and gpa_credits
            else unweighted_gpa
        )

        program = first.program_id
        credits_required = program.total_credits if (program and program.total_credits) else 120

        if program and program.min_graduation_grade_id:
            passing_line = program.min_graduation_grade_id
        else:
            passing_lines = grade_lines.filtered(lambda line: line.is_passing).sorted("min_score")
            passing_line = passing_lines[:1]

        attendance = self.env["university.attendance"].search(
            [("student_id", "=", first.student_id.id)]
        )
        attendance_rate = False
        if attendance:
            statuses = {
                status: len(attendance.filtered(lambda item: item.status == status))
                for status in ("present", "absent", "late", "excused")
            }
            attendance_rate = self.env["university.attendance"]._attendance_percentage(statuses)

        graduation_date = getattr(first, "graduation_date", False) or getattr(
            first.student_id, "graduation_date", False
        )

        # Academic Years structure (ordered chronologically oldest first)
        years = first.line_ids.mapped("academic_year_id").sorted(
            key=lambda y: (y.date_start or fields.Date.min, y.name or "", y.id)
        )

        years_data = []
        for y_idx, year in enumerate(years):
            y_lines = first.line_ids.filtered(lambda l: l.academic_year_id == year)

            s1_lines = y_lines.filtered(
                lambda l: "1" in (l.semester_id.name or "") or "First" in (l.semester_id.name or "")
            )
            s2_lines = y_lines.filtered(
                lambda l: "2" in (l.semester_id.name or "") or "Second" in (l.semester_id.name or "")
            )
            if not s1_lines and not s2_lines and y_lines:
                distinct_sems = y_lines.mapped("semester_id").sorted(
                    key=lambda s: (s.date_start or fields.Date.min, s.name or "")
                )
                s1_lines = y_lines.filtered(lambda l: l.semester_id == distinct_sems[:1])
                s2_lines = y_lines.filtered(lambda l: l.semester_id in distinct_sems[1:2])

            s1_record = (
                s1_lines.mapped("semester_id")[:1]
                or year.semester_ids.filtered(lambda s: "1" in (s.name or "") or "First" in (s.name or ""))[:1]
            )
            s2_record = (
                s2_lines.mapped("semester_id")[:1]
                or year.semester_ids.filtered(lambda s: "2" in (s.name or "") or "Second" in (s.name or ""))[:1]
            )

            def get_sem_status(lines, sem_rec):
                if lines:
                    return False
                if sem_rec and sem_rec.date_end:
                    if sem_rec.date_end < today:
                        return "No enrollment"
                    else:
                        return "In progress"
                if year.date_start and year.date_start > today:
                    return "In progress"
                return "No enrollment"

            s1_credits = sum(s1_lines.mapped("credits"))
            s1_pts = sum((l.credits or 0) * (l.grade_point or 0.0) for l in s1_lines)
            s1_gpa = (s1_pts / s1_credits) if s1_credits else 0.0

            s2_credits = sum(s2_lines.mapped("credits"))
            s2_pts = sum((l.credits or 0) * (l.grade_point or 0.0) for l in s2_lines)
            s2_gpa = (s2_pts / s2_credits) if s2_credits else 0.0

            years_data.append({
                "year": year,
                "year_number": y_idx + 1,
                "s1_lines": s1_lines,
                "s1_credits": s1_credits,
                "s1_gpa": s1_gpa,
                "s1_status": get_sem_status(s1_lines, s1_record),
                "s2_lines": s2_lines,
                "s2_credits": s2_credits,
                "s2_gpa": s2_gpa,
                "s2_status": get_sem_status(s2_lines, s2_record),
            })

        company = first.company_id or self.env.company
        addr_parts = [
            part for part in [
                company.street,
                company.city,
                company.state_id.name if company.state_id else None,
                company.country_id.name if company.country_id else None,
                company.zip,
            ] if part
        ]
        company_address = ", ".join(addr_parts)

        return {
            "doc_ids": docs.ids,
            "doc_model": "university.transcript",
            "docs": docs,
            "scale_id": scale,
            "grade_lines": grade_lines,
            "has_honors_grade_point": has_honors,
            "honors_denominator": weighted_max,
            "weighted_max": weighted_max,
            "unweighted_max": unweighted_max,
            "weighted_gpa": weighted_gpa,
            "unweighted_gpa": unweighted_gpa,
            "total_credits": total_credits,
            "credits_required": credits_required,
            "passing_line": passing_line,
            "attendance_rate": attendance_rate,
            "graduation_date": graduation_date,
            "years_data": years_data,
            "repeated_line_ids": repeated_line_ids,
            "company_address": company_address,
        }
'''

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("academic_report.py updated successfully!")
