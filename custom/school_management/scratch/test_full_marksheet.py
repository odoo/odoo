import io
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_col_to_name

def build_marksheet_xlsx(title, subtitle, full_marks, pass_marks, subjects, students, exam_info=None):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet('Student Marksheet')
    sheet.hide_gridlines(0)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)

    # Theme Colors
    C_NAVY_DARK = '#1B365D'
    C_NAVY_MED = '#2C5282'
    C_SLATE_LIGHT = '#F1F5F9'
    C_SLATE_BORDER = '#CBD5E1'
    C_ZEBRA = '#F8FAFC'
    C_GREEN_BG = '#DCFCE7'
    C_GREEN_TXT = '#166534'
    C_RED_BG = '#FEE2E2'
    C_RED_TXT = '#991B1B'
    C_AMBER_BG = '#FEF3C7'
    C_AMBER_TXT = '#92400E'
    C_PURPLE_BG = '#F3E8FF'
    C_PURPLE_TXT = '#6B21A8'

    # Cell Formats
    f_brand_title = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_NAVY_DARK, 'font_color': '#FFFFFF', 'border': 1, 'border_color': C_NAVY_DARK
    })
    f_brand_sub = workbook.add_format({
        'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_NAVY_MED, 'font_color': '#FFFFFF', 'border': 1, 'border_color': C_NAVY_MED
    })
    f_meta_lbl = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'right', 'valign': 'vcenter',
        'bg_color': C_SLATE_LIGHT, 'font_color': '#334155', 'border': 1, 'border_color': C_SLATE_BORDER
    })
    f_meta_val = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'left', 'valign': 'vcenter',
        'bg_color': '#FFFFFF', 'font_color': '#0F172A', 'border': 1, 'border_color': C_SLATE_BORDER
    })
    f_meta_val_center = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#FFFFFF', 'font_color': '#0F172A', 'border': 1, 'border_color': C_SLATE_BORDER
    })
    f_meta_pass = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_GREEN_BG, 'font_color': C_GREEN_TXT, 'border': 1, 'border_color': C_SLATE_BORDER
    })
    f_meta_status = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#DBEAFE', 'font_color': '#1E40AF', 'border': 1, 'border_color': C_SLATE_BORDER
    })

    # Table Header Formats
    f_th = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_NAVY_DARK, 'font_color': '#FFFFFF', 'border': 1, 'border_color': '#0F172A', 'text_wrap': True
    })

    # Data Formats
    f_data_center = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER})
    f_data_center_zebra = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_ZEBRA})
    f_data_name = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER})
    f_data_name_zebra = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_ZEBRA})
    f_data_num = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'num_format': '0.00'})
    f_data_num_zebra = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_ZEBRA, 'num_format': '0.00'})
    f_data_final = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': '#F1F5F9', 'num_format': '0.00'})
    f_data_pct = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': '#F8FAFC', 'num_format': '0.0%'})
    f_data_present = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'font_color': C_GREEN_TXT, 'bg_color': '#F0FDF4'})
    f_data_absent = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'font_color': C_RED_TXT, 'bg_color': '#FEF2F2'})
    f_data_pass = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_GREEN_BG, 'font_color': C_GREEN_TXT})
    f_data_fail = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_RED_BG, 'font_color': C_RED_TXT})
    f_data_absent_badge = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_AMBER_BG, 'font_color': C_AMBER_TXT})
    f_data_grade = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_SLATE_LIGHT})
    f_data_rank = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_PURPLE_BG, 'font_color': C_PURPLE_TXT})
    f_data_remark = workbook.add_format({'font_size': 9, 'italic': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER})
    f_data_remark_zebra = workbook.add_format({'font_size': 9, 'italic': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_ZEBRA})

    # Summary Formats
    f_sec_hdr = workbook.add_format({'bold': True, 'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'bg_color': '#334155', 'font_color': '#FFFFFF', 'border': 1})
    f_stat_lbl = workbook.add_format({'bold': True, 'font_size': 9, 'align': 'left', 'valign': 'vcenter', 'bg_color': C_SLATE_LIGHT, 'border': 1, 'border_color': C_SLATE_BORDER})
    f_stat_val = workbook.add_format({'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'num_format': '0.00'})
    f_stat_val_int = workbook.add_format({'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'num_format': '#,##0'})
    f_stat_highlight = workbook.add_format({'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_GREEN_BG, 'font_color': C_GREEN_TXT, 'num_format': '0.0%'})
    f_sig_lbl = workbook.add_format({'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'bg_color': C_SLATE_LIGHT, 'border': 1, 'border_color': C_SLATE_BORDER})
    f_sig_line = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'bottom', 'border': 1, 'border_color': C_SLATE_BORDER, 'italic': True, 'font_color': '#64748b'})
    f_footer_note = workbook.add_format({'font_size': 8, 'italic': True, 'font_color': '#64748b', 'align': 'center', 'valign': 'vcenter'})

    info = exam_info or {}
    last_col = 11

    # Row Heights
    sheet.set_row(0, 32)
    sheet.set_row(1, 22)
    sheet.set_row(2, 6)
    sheet.set_row(3, 20)
    sheet.set_row(4, 20)
    sheet.set_row(5, 20)
    sheet.set_row(6, 20)
    sheet.set_row(7, 8)
    sheet.set_row(8, 26)

    # 1. Header Banner
    institution = info.get('institution', 'HARVARD UNIVERSITY · FACULTY ACADEMIC AFFAIRS')
    doc_title = title or 'OFFICIAL STUDENT EXAMINATION MARKSHEET'
    sheet.merge_range(0, 0, 0, last_col, institution.upper(), f_brand_title)
    sheet.merge_range(1, 0, 1, last_col, doc_title.upper() + ' · ' + (subtitle or ''), f_brand_sub)

    # 2. Metadata Grid
    # Row 3
    sheet.write(3, 0, 'Course / Subject:', f_meta_lbl)
    sheet.merge_range(3, 1, 3, 3, info.get('course', subjects[0] if subjects else 'Course'), f_meta_val)
    sheet.merge_range(3, 4, 3, 5, 'Academic Period:', f_meta_lbl)
    sheet.merge_range(3, 6, 3, 8, info.get('academic_period', 'Academic Year & Term'), f_meta_val)
    sheet.merge_range(3, 9, 3, 10, 'Max Score:', f_meta_lbl)
    sheet.write(3, 11, f'{full_marks:.2f} pts', f_meta_val_center)

    # Row 4
    sheet.write(4, 0, 'Class Section:', f_meta_lbl)
    sheet.merge_range(4, 1, 3 + 0, info.get('section', 'Class Section'), f_meta_val)
    # wait, merge_range(4, 1, 4, 3)
    sheet.merge_range(4, 1, 4, 3, info.get('section', 'Class Section'), f_meta_val)
    sheet.merge_range(4, 4, 4, 5, 'Program / Major:', f_meta_lbl)
    sheet.merge_range(4, 6, 4, 8, info.get('program', 'Academic Program'), f_meta_val)
    sheet.merge_range(4, 9, 4, 10, 'Passing Score:', f_meta_lbl)
    sheet.write(4, 11, f'{pass_marks:.2f} pts (50%)', f_meta_pass)

    # Row 5
    sheet.write(5, 0, 'Instructor / Teacher:', f_meta_lbl)
    sheet.merge_range(5, 1, 5, 3, info.get('teacher', 'Course Instructor'), f_meta_val)
    sheet.merge_range(5, 4, 5, 5, 'Department:', f_meta_lbl)
    sheet.merge_range(5, 6, 5, 8, info.get('department', 'Academic Department'), f_meta_val)
    sheet.merge_range(5, 9, 5, 10, 'Exam Weight:', f_meta_lbl)
    sheet.write(5, 11, info.get('weight', 'Course Component'), f_meta_val_center)

    # Row 6
    sheet.write(6, 0, 'Exam Type:', f_meta_lbl)
    sheet.merge_range(6, 1, 6, 3, info.get('exam_type', 'Examination'), f_meta_status)
    sheet.merge_range(6, 4, 6, 5, 'Date & Duration:', f_meta_lbl)
    sheet.merge_range(6, 6, 6, 8, info.get('exam_date_duration', 'Scheduled Date'), f_meta_val)
    sheet.merge_range(6, 9, 6, 10, 'Exam Status:', f_meta_lbl)
    sheet.write(6, 11, info.get('status', 'Completed'), f_meta_status)

    # 3. Table Column Headers (Row 8)
    headers = [
        ('No.', 5),
        ('Student ID', 16),
        ('Student Name', 26),
        ('Attendance', 13),
        ('Raw Score', 12),
        ('Penalty', 11),
        ('Final Score', 13),
        ('Percentage', 13),
        ('Result', 12),
        ('Grade', 10),
        ('Rank', 11),
        ('Remark', 22),
    ]
    for c_idx, (h_title, col_w) in enumerate(headers):
        sheet.write(8, c_idx, h_title, f_th)
        sheet.set_column(c_idx, c_idx, col_w)

    # 4. Data Rows
    start_r = 9
    num_students = len(students)
    totals_list = [stu.get('final_score', (stu.get('marks', [0])[0] if stu.get('marks') else 0.0)) for stu in students]
    sorted_totals = sorted(totals_list, reverse=True)

    for i, stu in enumerate(students):
        r = start_r + i
        is_zebra = (i % 2 == 1)
        c_zebra = f_data_center_zebra if is_zebra else f_data_center
        n_zebra = f_data_name_zebra if is_zebra else f_data_name
        num_z = f_data_num_zebra if is_zebra else f_data_num
        rem_z = f_data_remark_zebra if is_zebra else f_data_remark

        sheet.set_row(r, 20)
        # Col 0: Seq
        sheet.write(r, 0, i + 1, c_zebra)
        # Col 1: ID
        sheet.write(r, 1, stu.get('id', ''), c_zebra)
        # Col 2: Name
        sheet.write(r, 2, stu.get('name', ''), n_zebra)
        # Col 3: Attendance
        is_absent = stu.get('is_absent', False)
        att_str = 'Absent' if is_absent else 'Present'
        sheet.write(r, 3, att_str, f_data_absent if is_absent else f_data_present)
        # Col 4: Raw Score
        raw_val = stu.get('raw_score', (stu.get('marks', [0])[0] if stu.get('marks') else 0.0))
        sheet.write(r, 4, raw_val if not is_absent else 0.0, num_z)
        # Col 5: Penalty
        penalty_val = stu.get('penalty', 0.0)
        sheet.write(r, 5, f'{penalty_val:.1f}%' if penalty_val else '0%', c_zebra)

        # Col 6: Final Score Formula
        final_val = 0.0 if is_absent else round(stu.get('final_score', raw_val), 2)
        r_excel = r + 1
        formula_final = f'=IF(D{r_excel}="Absent",0.00,ROUND(E{r_excel}*(1-F{r_excel}/100),2))' if penalty_val else f'=IF(D{r_excel}="Absent",0.00,E{r_excel})'
        sheet.write_formula(r, 6, formula_final, f_data_final, final_val)

        # Col 7: Percentage Formula (=G{r}/full_marks)
        pct_val = (final_val / full_marks) if full_marks > 0 else 0.0
        formula_pct = f'=G{r_excel}/{full_marks:.2f}'
        sheet.write_formula(r, 7, formula_pct, f_data_pct, pct_val)

        # Col 8: Result Formula (=IF(D="Absent","ABSENT",IF(G>=pass_marks,"PASS","FAIL")))
        res_str = 'ABSENT' if is_absent else ('PASS' if final_val >= pass_marks else 'FAIL')
        res_format = f_data_absent_badge if is_absent else (f_data_pass if final_val >= pass_marks else f_data_fail)
        formula_res = f'=IF(D{r_excel}="Absent","ABSENT",IF(G{r_excel}>={pass_marks:.2f},"PASS","FAIL"))'
        sheet.write_formula(r, 8, formula_res, res_format, res_str)

        # Col 9: Grade Formula
        pct_100 = pct_val * 100.0
        grade_str = '-' if is_absent else ('A' if pct_100 >= 90 else ('B' if pct_100 >= 80 else ('C' if pct_100 >= 70 else ('D' if pct_100 >= 60 else 'F'))))
        formula_grade = f'=IF(D{r_excel}="Absent","-",IF(H{r_excel}>=0.9,"A",IF(H{r_excel}>=0.8,"B",IF(H{r_excel}>=0.7,"C",IF(H{r_excel}>=0.6,"D","F")))))'
        sheet.write_formula(r, 9, formula_grade, f_data_grade, grade_str)

        # Col 10: Rank Formula
        rank_val = sorted_totals.index(final_val) + 1 if (num_students > 0 and not is_absent) else '-'
        end_r_excel = start_r + num_students
        formula_rank = f'=IF(D{r_excel}="Absent","-",RANK(G{r_excel},:))'
        sheet.write_formula(r, 10, formula_rank, f_data_rank, rank_val if isinstance(rank_val, int) else 1)

        # Col 11: Remarks
        rem_str = stu.get('remark', '') or ('Absent' if is_absent else ('Passed with Distinction' if pct_100 >= 90 else ('Passed' if final_val >= pass_marks else 'Failed')))
        sheet.write(r, 11, rem_str, rem_z)

    # Freeze panes below headers
    sheet.freeze_panes(start_r, 0)

    # 5. Class Analytics & Summary Statistics Section
    if num_students > 0:
        stat_r = start_r + num_students + 1
        sheet.set_row(stat_r, 6)
        stat_r += 1

        # Section Header
        sheet.set_row(stat_r, 22)
        sheet.merge_range(stat_r, 0, stat_r, 5, '  CLASS EXAMINATION PERFORMANCE ANALYTICS', f_sec_hdr)
        sheet.merge_range(stat_r, 6, stat_r, last_col, '  GRADE DISTRIBUTION BREAKDOWN', f_sec_hdr)

        first_data = start_r + 1
        last_data = start_r + num_students

        stats_data = [
            ('Total Students Enrolled', f'=COUNTA(B{first_data}:B{last_data})', num_students, f_stat_val_int),
            ('Students Present', f'=COUNTIF(D{first_data}:D{last_data},"Present")', sum(1 for s in students if not s.get('is_absent')), f_stat_val_int),
            ('Students Absent', f'=COUNTIF(D{first_data}:D{last_data},"Absent")', sum(1 for s in students if s.get('is_absent')), f_stat_val_int),
            ('Class Average Score', f'=IFERROR(ROUND(AVERAGEIF(D{first_data}:D{last_data},"Present",G{first_data}:G{last_data}),2),0.00)', info.get('avg_score', 0.0), f_stat_val),
            ('Highest Score', f'=IFERROR(MAX(G{first_data}:G{last_data}),0.00)', max(totals_list) if totals_list else 0.0, f_stat_val),
            ('Lowest Score (Present)', f'=IFERROR(MINIFS(G{first_data}:G{last_data},D{first_data}:D{last_data},"Present"),0.00)', min(totals_list) if totals_list else 0.0, f_stat_val),
            ('Passed Students', f'=COUNTIF(I{first_data}:I{last_data},"PASS")', sum(1 for s in students if not s.get('is_absent') and s.get('final_score', 0) >= pass_marks), f_stat_val_int),
            ('Failed Students', f'=COUNTIF(I{first_data}:I{last_data},"FAIL")', sum(1 for s in students if not s.get('is_absent') and s.get('final_score', 0) < pass_marks), f_stat_val_int),
            ('Class Passing Rate', f'=IFERROR(ROUND(COUNTIF(I{first_data}:I{last_data},"PASS")/MAX(1,COUNTIF(D{first_data}:D{last_data},"Present")),4),0.0000)', (sum(1 for s in students if not s.get('is_absent') and s.get('final_score', 0) >= pass_marks) / max(1, sum(1 for s in students if not s.get('is_absent')))), f_stat_highlight),
        ]

        grade_breakdown = [
            ('Grade A (90% - 100%)', f'=COUNTIF(J{first_data}:J{last_data},"A")'),
            ('Grade B (80% - 89%)', f'=COUNTIF(J{first_data}:J{last_data},"B")'),
            ('Grade C (70% - 79%)', f'=COUNTIF(J{first_data}:J{last_data},"C")'),
            ('Grade D (60% - 69%)', f'=COUNTIF(J{first_data}:J{last_data},"D")'),
            ('Grade F (Below 60%)', f'=COUNTIF(J{first_data}:J{last_data},"F")'),
            ('Absent / Incomplete', f'=COUNTIF(D{first_data}:D{last_data},"Absent")'),
        ]

        for s_idx, (lbl, formula, cached_v, val_fmt) in enumerate(stats_data):
            curr_r = stat_r + 1 + s_idx
            sheet.set_row(curr_r, 19)
            sheet.merge_range(curr_r, 0, curr_r, 3, lbl, f_stat_lbl)
            sheet.merge_range(curr_r, 4, curr_r, 5, formula, val_fmt, cached_v)

            if s_idx < len(grade_breakdown):
                g_lbl, g_formula = grade_breakdown[s_idx]
                sheet.merge_range(curr_r, 6, curr_r, 9, g_lbl, f_stat_lbl)
                sheet.merge_range(curr_r, 10, curr_r, 11, g_formula, f_stat_val_int, 0)

        # 6. Sign-off / Verification Section
        sig_r = stat_r + len(stats_data) + 2
        sheet.set_row(sig_r, 20)
        sheet.merge_range(sig_r, 0, sig_r, 3, 'Prepared By (Instructor)', f_sig_lbl)
        sheet.merge_range(sig_r, 4, sig_r, 7, 'Verified By (Department Head)', f_sig_lbl)
        sheet.merge_range(sig_r, 8, sig_r, 11, 'Approved By (Academic Registrar / Dean)', f_sig_lbl)

        for line_offset in range(1, 4):
            sheet.set_row(sig_r + line_offset, 18)
            if line_offset == 1:
                t_name = info.get('teacher', 'Instructor Signature')
                d_name = info.get('department', 'Department Head')
                sheet.merge_range(sig_r + line_offset, 0, sig_r + line_offset, 3, t_name, f_data_center)
                sheet.merge_range(sig_r + line_offset, 4, sig_r + line_offset, 7, d_name, f_data_center)
                sheet.merge_range(sig_r + line_offset, 8, sig_r + line_offset, 11, 'Office of Academic Affairs', f_data_center)
            elif line_offset == 2:
                sheet.merge_range(sig_r + line_offset, 0, sig_r + line_offset, 3, 'Signature: _______________________', f_sig_line)
                sheet.merge_range(sig_r + line_offset, 4, sig_r + line_offset, 7, 'Signature: _______________________', f_sig_line)
                sheet.merge_range(sig_r + line_offset, 8, sig_r + line_offset, 11, 'Official University Seal / Signature', f_sig_line)
            elif line_offset == 3:
                sheet.merge_range(sig_r + line_offset, 0, sig_r + line_offset, 3, 'Date: _____ / _____ / 202___', f_sig_line)
                sheet.merge_range(sig_r + line_offset, 4, sig_r + line_offset, 7, 'Date: _____ / _____ / 202___', f_sig_line)
                sheet.merge_range(sig_r + line_offset, 8, sig_r + line_offset, 11, 'Date: _____ / _____ / 202___', f_sig_line)

        # 7. Official Footer
        foot_r = sig_r + 5
        sheet.merge_range(foot_r, 0, foot_r, last_col, 'CONFIDENTIAL · This marksheet is an official academic record produced by the University Management Portal. Any unauthorized alteration or forgery is subject to disciplinary and legal action.', f_footer_note)

    workbook.close()
    return output.getvalue()

print('build_marksheet_xlsx compiled successfully!')
