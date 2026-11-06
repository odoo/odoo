path = r"custom\school_management\models\grading.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_section = '''    @api.depends("line_ids.credits", "line_ids.grade_point")
    def _compute_cumulative_gpa(self):
        for transcript in self:
            credits = sum(transcript.line_ids.mapped("credits"))
            quality = sum(line.credits * line.grade_point for line in transcript.line_ids)
            transcript.total_credits = credits
            transcript.cumulative_gpa = quality / credits if credits else 0.0

    @api.depends(
        "student_id.report_card_ids.academic_standing",
        "student_id.report_card_ids.state",
        "cumulative_gpa",
        "total_credits",
    )
    def _compute_academic_standing(self):
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            min_gpa = float(ICP.get_param("school_management.deans_list_min_gpa", 3.5))
        except (ValueError, TypeError):
            min_gpa = 3.5
        try:
            min_credits = float(ICP.get_param("school_management.deans_list_min_credits", 12))
        except (ValueError, TypeError):
            min_credits = 12.0

        for transcript in self:
            latest_card = self.env["university.report.card"].search(
                [
                    ("student_id", "=", transcript.student_id.id),
                    ("state", "in", ["generated", "approved"]),
                ],
                order="academic_year_id desc, semester_id desc, id desc",
                limit=1,
            )
            if latest_card:
                transcript.academic_standing = latest_card.academic_standing
            else:
                if transcript.cumulative_gpa >= min_gpa and transcript.total_credits >= min_credits:
                    transcript.academic_standing = "dean_list"
                elif transcript.cumulative_gpa >= 2.0:
                    transcript.academic_standing = "good"
                else:
                    transcript.academic_standing = "probation"

    def action_generate_lines(self):
        for transcript in self:
            cards = self.env["university.report.card"].search(
                [
                    ("student_id", "=", transcript.student_id.id),
                    ("state", "in", ["generated", "approved"]),
                ],
                order="academic_year_id, semester_id, id",
            )
            lines = [(5, 0, 0)]
            for card in cards:
                for card_line in card.line_ids:
                    lines.append(
                        (
                            0,
                            0,
                            {
                                "academic_year_id": card.academic_year_id.id,
                                "semester_id": card.semester_id.id,
                                "subject_id": card_line.subject_id.id,
                                "credits": card_line.credits,
                                "final_score": card_line.final_score,
                                "grade": card_line.grade,
                                "grade_point": card_line.grade_point,
                                "is_passing": card_line.is_passing,
                            },
                        )
                    )
            vals = {"line_ids": lines, "state": "generated"}
            scale = cards.mapped("grade_scale_id")[:1]
            if scale:
                vals["grade_scale_id"] = scale.id
            transcript.write(vals)'''

new_section = '''    @api.depends("line_ids.credits", "line_ids.grade_point", "line_ids.subject_id")
    def _compute_cumulative_gpa(self):
        for transcript in self:
            subject_lines = {}
            for line in transcript.line_ids:
                subject_lines.setdefault(line.subject_id.id, []).append(line)

            best_lines = []
            for sub_id, l_list in subject_lines.items():
                if len(l_list) == 1:
                    best_lines.append(l_list[0])
                else:
                    sorted_attempts = sorted(
                        l_list,
                        key=lambda l: (
                            l.grade_point or 0.0,
                            l.academic_year_id.date_start or fields.Date.min,
                            l.semester_id.date_start or fields.Date.min,
                            l.id or 0,
                        ),
                        reverse=True,
                    )
                    best_lines.append(sorted_attempts[0])

            effective_credits = sum(l.credits for l in best_lines if l.is_passing or (l.grade_point or 0.0) > 0)
            quality = sum(l.credits * (l.grade_point or 0.0) for l in best_lines)
            gpa_credits = sum(l.credits for l in best_lines)

            transcript.total_credits = effective_credits
            transcript.cumulative_gpa = quality / gpa_credits if gpa_credits else 0.0

    @api.depends(
        "student_id.report_card_ids.academic_standing",
        "student_id.report_card_ids.state",
        "cumulative_gpa",
        "total_credits",
    )
    def _compute_academic_standing(self):
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            min_gpa = float(ICP.get_param("school_management.deans_list_min_gpa", 3.5))
        except (ValueError, TypeError):
            min_gpa = 3.5
        try:
            min_credits = float(ICP.get_param("school_management.deans_list_min_credits", 12))
        except (ValueError, TypeError):
            min_credits = 12.0

        for transcript in self:
            cards = self.env["university.report.card"].search(
                [
                    ("student_id", "=", transcript.student_id.id),
                    ("state", "in", ["generated", "approved"]),
                ]
            )
            # Find chronologically latest card
            cards_sorted = cards.sorted(
                key=lambda c: (
                    c.academic_year_id.date_start or fields.Date.min,
                    c.semester_id.date_start or fields.Date.min,
                    c.id,
                ),
                reverse=True,
            )
            latest_card = cards_sorted[:1]
            if transcript.cumulative_gpa >= min_gpa and transcript.total_credits >= min_credits:
                transcript.academic_standing = "dean_list"
            elif latest_card and latest_card.academic_standing == "dean_list":
                transcript.academic_standing = "dean_list"
            elif transcript.cumulative_gpa >= 2.0:
                transcript.academic_standing = "good"
            else:
                transcript.academic_standing = "probation"

    def action_generate_lines(self):
        for transcript in self:
            cards = self.env["university.report.card"].search(
                [
                    ("student_id", "=", transcript.student_id.id),
                    ("state", "in", ["generated", "approved"]),
                ]
            )
            cards = cards.sorted(
                key=lambda c: (
                    c.academic_year_id.date_start or fields.Date.min,
                    c.semester_id.date_start or fields.Date.min,
                    c.id,
                )
            )
            raw_lines = []
            for card in cards:
                for card_line in card.line_ids:
                    raw_lines.append({
                        "academic_year_id": card.academic_year_id.id,
                        "semester_id": card.semester_id.id,
                        "subject_id": card_line.subject_id.id,
                        "credits": card_line.credits,
                        "final_score": card_line.final_score,
                        "grade": card_line.grade,
                        "grade_point": card_line.grade_point,
                        "is_passing": card_line.is_passing,
                        "date_sort": (
                            card.academic_year_id.date_start or fields.Date.min,
                            card.semester_id.date_start or fields.Date.min,
                        ),
                    })

            subject_groups = {}
            for item in raw_lines:
                subject_groups.setdefault(item["subject_id"], []).append(item)

            for sub_id, items in subject_groups.items():
                if len(items) == 1:
                    items[0]["is_repeated"] = False
                    items[0]["counts_for_credits"] = True
                else:
                    sorted_items = sorted(
                        items,
                        key=lambda x: (x["grade_point"] or 0.0, x["date_sort"]),
                        reverse=True,
                    )
                    sorted_items[0]["is_repeated"] = False
                    sorted_items[0]["counts_for_credits"] = True
                    for rep in sorted_items[1:]:
                        rep["is_repeated"] = True
                        rep["counts_for_credits"] = False

            lines = [(5, 0, 0)]
            for item in raw_lines:
                vals_line = dict(item)
                vals_line.pop("date_sort", None)
                lines.append((0, 0, vals_line))

            vals = {"line_ids": lines, "state": "generated"}
            scale = cards.mapped("grade_scale_id")[:1]
            if scale:
                vals["grade_scale_id"] = scale.id
            transcript.write(vals)'''

assert old_section in content, "old_section not found in grading.py"
content = content.replace(old_section, new_section, 1)

line_target = '    is_passing = fields.Boolean(string="Passing")'
line_addition = '''    is_passing = fields.Boolean(string="Passing")
    is_repeated = fields.Boolean(string="Repeated Course", default=False)
    counts_for_credits = fields.Boolean(string="Counts For Credits", default=True)'''

assert line_target in content, "line_target not found in grading.py"
content = content.replace(line_target, line_addition, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("grading.py patched successfully!")
