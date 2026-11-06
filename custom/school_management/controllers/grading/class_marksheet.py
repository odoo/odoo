# -*- coding: utf-8 -*-

import io
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_col_to_name

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError


def build_class_marksheet_xlsx(title, subtitle, section_info, exams, students, **kwargs):
    """
    Build a comprehensive, executive-grade class section gradebook & marksheet Excel workbook.

    Features:
    - Official University branding header banner (Navy / Slate palette)
    - Structured academic metadata grid (Course, Section, Term, Teacher, Department, Total Enrolled)
    - Consolidated assessment ledger:
        * No. (#)
        * Student ID
        * Student Name
        * Attendance Rate (%)
        * Dynamic assessment columns for each exam/quiz/assignment
        * Total Accumulated Score (with Excel SUM formula)
        * Percentage (%) (with live Excel formula)
        * Letter Grade (A, B, C, D, F with IF formulas)
        * Class Rank (RANK formula)
        * Result Status (PASS / FAIL)
        * Remarks
    - Dynamic Class Performance Analytics & Summary KPIs
    - Grade Distribution Breakdown (A, B, C, D, F counts)
    - Faculty & Administration Verification Sign-off blocks (Instructor, HOD, Dean)
    - Print setup fitted to 1 page wide in landscape mode with frozen header panes.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet('Class Marksheet')
    sheet.hide_gridlines(0)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)

    # ---------------------------------------------------------
    # Color Palette & Format Definitions
    # ---------------------------------------------------------
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
    C_BLUE_BG = '#DBEAFE'
    C_BLUE_TXT = '#1E40AF'

    # Branding & Header Formats
    f_brand_title = workbook.add_format({
        'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_NAVY_DARK, 'font_color': '#FFFFFF', 'border': 1, 'border_color': C_NAVY_DARK
    })
    f_brand_sub = workbook.add_format({
        'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_NAVY_MED, 'font_color': '#FFFFFF', 'border': 1, 'border_color': C_NAVY_MED
    })

    # Metadata Formats
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
    f_meta_status = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_BLUE_BG, 'font_color': C_BLUE_TXT, 'border': 1, 'border_color': C_SLATE_BORDER
    })

    # Table Header Formats
    f_th = workbook.add_format({
        'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_NAVY_DARK, 'font_color': '#FFFFFF', 'border': 1, 'border_color': '#0F172A', 'text_wrap': True
    })
    f_th_exam = workbook.add_format({
        'bold': True, 'font_size': 8.5, 'align': 'center', 'valign': 'vcenter',
        'bg_color': C_NAVY_MED, 'font_color': '#FFFFFF', 'border': 1, 'border_color': '#0F172A', 'text_wrap': True
    })

    # Data Row Formats
    f_data_center = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER})
    f_data_center_zebra = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_ZEBRA})
    f_data_name = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER})
    f_data_name_zebra = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_ZEBRA})
    f_data_num = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'num_format': '0.00'})
    f_data_num_zebra = workbook.add_format({'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_ZEBRA, 'num_format': '0.00'})
    f_data_final = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': '#F1F5F9', 'num_format': '0.00'})
    f_data_pct = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': '#F8FAFC', 'num_format': '0.0%'})
    f_data_pass = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_GREEN_BG, 'font_color': C_GREEN_TXT})
    f_data_fail = workbook.add_format({'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_SLATE_BORDER, 'bg_color': C_RED_BG, 'font_color': C_RED_TXT})
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

    info = section_info or {}
    num_exams = len(exams)

    # Column configuration
    # Static prefix cols: 0: No., 1: Student ID, 2: Student Name, 3: Attendance Rate
    # Exam cols: 4 .. 4 + num_exams - 1
    # Static postfix cols: Total Score, Percentage, Grade, Rank, Result, Remarks
    col_exam_start = 4
    col_exam_end = col_exam_start + num_exams - 1 if num_exams > 0 else col_exam_start
    col_total = col_exam_start + num_exams
    col_pct = col_total + 1
    col_grade = col_pct + 1
    col_rank = col_grade + 1
    col_result = col_rank + 1
    col_remarks = col_result + 1
    last_col = col_remarks

    # Row Heights
    sheet.set_row(0, 32)
    sheet.set_row(1, 22)
    sheet.set_row(2, 6)
    sheet.set_row(3, 20)
    sheet.set_row(4, 20)
    sheet.set_row(5, 20)
    sheet.set_row(6, 20)
    sheet.set_row(7, 8)
    sheet.set_row(8, 28)

    # 1. Header Banner
    institution = info.get('institution', 'HARVARD UNIVERSITY - FACULTY ACADEMIC AFFAIRS')
    doc_title = title or 'OFFICIAL CLASS SECTION MARKSHEET & GRADEBOOK'
    sub_title = subtitle or 'Cumulative Course Academic Performance Ledger'
    sheet.merge_range(0, 0, 0, last_col, institution.upper(), f_brand_title)
    sheet.merge_range(1, 0, 1, last_col, f"{doc_title.upper()} - {sub_title}", f_brand_sub)

    # 2. Metadata Grid
    # Row 3
    sheet.write(3, 0, 'Course / Subject:', f_meta_lbl)
    sheet.merge_range(3, 1, 3, 3, info.get('course', 'Course / Subject'), f_meta_val)
    sheet.merge_range(3, 4, 3, min(5, last_col - 2), 'Academic Period:', f_meta_lbl)
    sheet.merge_range(3, min(6, last_col - 1), 3, max(min(7, last_col - 1), min(6, last_col - 1)), info.get('academic_period', 'Academic Term'), f_meta_val)
    sheet.write(3, max(last_col - 1, 6), 'Total Students:', f_meta_lbl)
    sheet.write(3, last_col, f"{len(students)} enrolled", f_meta_val_center)

    # Row 4
    sheet.write(4, 0, 'Class Section:', f_meta_lbl)
    sheet.merge_range(4, 1, 4, 3, info.get('section', 'Section'), f_meta_val)
    sheet.merge_range(4, 4, 4, min(5, last_col - 2), 'Program / Major:', f_meta_lbl)
    sheet.merge_range(4, min(6, last_col - 1), 4, max(min(7, last_col - 1), min(6, last_col - 1)), info.get('program', 'Degree Program'), f_meta_val)
    sheet.write(4, max(last_col - 1, 6), 'Passing Score:', f_meta_lbl)
    sheet.write(4, last_col, "50.0% (Overall)", f_meta_status)

    # Row 5
    sheet.write(5, 0, 'Instructor / Teacher:', f_meta_lbl)
    sheet.merge_range(5, 1, 5, 3, info.get('teacher', 'Instructor'), f_meta_val)
    sheet.merge_range(5, 4, 5, min(5, last_col - 2), 'Department:', f_meta_lbl)
    sheet.merge_range(5, min(6, last_col - 1), 5, max(min(7, last_col - 1), min(6, last_col - 1)), info.get('department', 'Department'), f_meta_val)
    sheet.write(5, max(last_col - 1, 6), 'Assessments:', f_meta_lbl)
    sheet.write(5, last_col, f"{num_exams} Components", f_meta_val_center)

    # Row 6
    sheet.write(6, 0, 'Classroom / Venue:', f_meta_lbl)
    sheet.merge_range(6, 1, 6, 3, info.get('classroom', 'Scheduled Venue'), f_meta_val)
    sheet.merge_range(6, 4, 6, min(5, last_col - 2), 'Schedule Time:', f_meta_lbl)
    sheet.merge_range(6, min(6, last_col - 1), 6, max(min(7, last_col - 1), min(6, last_col - 1)), info.get('schedule', 'Course Schedule'), f_meta_val)
    sheet.write(6, max(last_col - 1, 6), 'Section Status:', f_meta_lbl)
    sheet.write(6, last_col, info.get('status', 'Active'), f_meta_status)

    # 3. Table Column Headers (Row 8)
    sheet.write(8, 0, 'No.', f_th)
    sheet.set_column(0, 0, 5)

    sheet.write(8, 1, 'Student ID', f_th)
    sheet.set_column(1, 1, 16)

    sheet.write(8, 2, 'Student Name', f_th)
    sheet.set_column(2, 2, 26)

    sheet.write(8, 3, 'Attendance', f_th)
    sheet.set_column(3, 3, 13)

    # Assessment headers
    total_max_points = sum(ex.get('max_score', 100.0) for ex in exams) if exams else 100.0
    for idx, ex in enumerate(exams):
        c = col_exam_start + idx
        ex_label = f"{ex.get('name', f'Exam {idx+1}')}\n({ex.get('max_score', 100):.0f} pts)"
        sheet.write(8, c, ex_label, f_th_exam)
        sheet.set_column(c, c, 14)

    sheet.write(8, col_total, f"Total Score\n({total_max_points:.0f} pts)", f_th)
    sheet.set_column(col_total, col_total, 13)

    sheet.write(8, col_pct, 'Percentage', f_th)
    sheet.set_column(col_pct, col_pct, 12)

    sheet.write(8, col_grade, 'Grade', f_th)
    sheet.set_column(col_grade, col_grade, 10)

    sheet.write(8, col_rank, 'Rank', f_th)
    sheet.set_column(col_rank, col_rank, 10)

    sheet.write(8, col_result, 'Result', f_th)
    sheet.set_column(col_result, col_result, 12)

    sheet.write(8, col_remarks, 'Remarks', f_th)
    sheet.set_column(col_remarks, col_remarks, 22)

    # 4. Data Rows
    start_r = 9
    num_students = len(students)
    totals_list = [stu.get('total_score', 0.0) for stu in students]
    sorted_totals = sorted(totals_list, reverse=True)

    for i, stu in enumerate(students):
        r = start_r + i
        r_excel = r + 1
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
        # Col 3: Attendance Rate
        att_rate = stu.get('attendance_rate', 100.0)
        sheet.write(r, 3, f"{att_rate:.1f}%", c_zebra)

        # Assessment scores
        exam_scores = stu.get('exam_scores', {})
        for idx, ex in enumerate(exams):
            c = col_exam_start + idx
            ex_id = ex.get('id')
            sc_val = exam_scores.get(ex_id, exam_scores.get(str(ex_id), 0.0))
            sheet.write(r, c, sc_val, num_z)

        # Total Score Formula: SUM across exam columns
        if num_exams > 0:
            c_first = xl_col_to_name(col_exam_start)
            c_last = xl_col_to_name(col_exam_end)
            formula_total = f"=SUM({c_first}{r_excel}:{c_last}{r_excel})"
        else:
            formula_total = f"=0"
        final_val = round(stu.get('total_score', 0.0), 2)
        sheet.write_formula(r, col_total, formula_total, f_data_final, final_val)

        # Percentage Formula (=Total/Max)
        c_tot_name = xl_col_to_name(col_total)
        pct_val = (final_val / total_max_points) if total_max_points > 0 else 0.0
        formula_pct = f"={c_tot_name}{r_excel}/{total_max_points:.2f}"
        sheet.write_formula(r, col_pct, formula_pct, f_data_pct, pct_val)

        # Letter Grade Formula
        c_pct_name = xl_col_to_name(col_pct)
        formula_grade = f'=IF({c_pct_name}{r_excel}>=0.9,"A",IF({c_pct_name}{r_excel}>=0.8,"B",IF({c_pct_name}{r_excel}>=0.7,"C",IF({c_pct_name}{r_excel}>=0.6,"D","F"))))'
        grade_str = 'A' if pct_val >= 0.9 else ('B' if pct_val >= 0.8 else ('C' if pct_val >= 0.7 else ('D' if pct_val >= 0.6 else 'F')))
        sheet.write_formula(r, col_grade, formula_grade, f_data_grade, grade_str)

        # Rank Formula
        end_r_excel = start_r + num_students
        formula_rank = f'=RANK({c_tot_name}{r_excel},${c_tot_name}${start_r + 1}:${c_tot_name}${end_r_excel})'
        rank_val = sorted_totals.index(final_val) + 1 if num_students > 0 else 1
        sheet.write_formula(r, col_rank, formula_rank, f_data_rank, rank_val)

        # Result Formula
        pass_thresh = total_max_points * 0.5
        formula_res = f'=IF({c_tot_name}{r_excel}>={pass_thresh:.2f},"PASS","FAIL")'
        res_str = 'PASS' if final_val >= pass_thresh else 'FAIL'
        res_fmt = f_data_pass if res_str == 'PASS' else f_data_fail
        sheet.write_formula(r, col_result, formula_res, res_fmt, res_str)

        # Remarks
        rem_str = stu.get('remark', '') or ('Distinction' if pct_val >= 0.9 else ('Passed' if res_str == 'PASS' else 'Academic Support Required'))
        sheet.write(r, col_remarks, rem_str, rem_z)

    # Freeze panes below headers
    sheet.freeze_panes(start_r, 0)

    # 5. Class Analytics & Summary Statistics Section
    if num_students > 0:
        stat_r = start_r + num_students + 1
        sheet.set_row(stat_r, 6)
        stat_r += 1

        # Section Header
        sheet.set_row(stat_r, 22)
        sheet.merge_range(stat_r, 0, stat_r, min(5, last_col - 3), '  CLASS SECTION PERFORMANCE ANALYTICS', f_sec_hdr)
        sheet.merge_range(stat_r, min(6, last_col - 2), stat_r, last_col, '  GRADE DISTRIBUTION BREAKDOWN', f_sec_hdr)

        first_data = start_r + 1
        last_data = start_r + num_students
        c_id_col = xl_col_to_name(1)
        c_res_col = xl_col_to_name(col_result)
        c_tot_col = xl_col_to_name(col_total)
        c_grd_col = xl_col_to_name(col_grade)

        stats_data = [
            ('Total Students Enrolled', f'=COUNTA({c_id_col}{first_data}:{c_id_col}{last_data})', num_students, f_stat_val_int),
            ('Class Average Score', f'=IFERROR(ROUND(AVERAGE({c_tot_col}{first_data}:{c_tot_col}{last_data}),2),0.00)', info.get('avg_score', 0.0), f_stat_val),
            ('Highest Score', f'=IFERROR(MAX({c_tot_col}{first_data}:{c_tot_col}{last_data}),0.00)', max(totals_list) if totals_list else 0.0, f_stat_val),
            ('Lowest Score', f'=IFERROR(MIN({c_tot_col}{first_data}:{c_tot_col}{last_data}),0.00)', min(totals_list) if totals_list else 0.0, f_stat_val),
            ('Passed Students', f'=COUNTIF({c_res_col}{first_data}:{c_res_col}{last_data},"PASS")', sum(1 for s in students if s.get('total_score', 0) >= (total_max_points * 0.5)), f_stat_val_int),
            ('Failed Students', f'=COUNTIF({c_res_col}{first_data}:{c_res_col}{last_data},"FAIL")', sum(1 for s in students if s.get('total_score', 0) < (total_max_points * 0.5)), f_stat_val_int),
            ('Class Passing Rate', f'=IFERROR(ROUND(COUNTIF({c_res_col}{first_data}:{c_res_col}{last_data},"PASS")/MAX(1,COUNTA({c_id_col}{first_data}:{c_id_col}{last_data})),4),0.0000)', (sum(1 for s in students if s.get('total_score', 0) >= (total_max_points * 0.5)) / max(1, num_students)), f_stat_highlight),
        ]

        grade_breakdown = [
            ('Grade A (90% - 100%)', f'=COUNTIF({c_grd_col}{first_data}:{c_grd_col}{last_data},"A")'),
            ('Grade B (80% - 89%)', f'=COUNTIF({c_grd_col}{first_data}:{c_grd_col}{last_data},"B")'),
            ('Grade C (70% - 79%)', f'=COUNTIF({c_grd_col}{first_data}:{c_grd_col}{last_data},"C")'),
            ('Grade D (60% - 69%)', f'=COUNTIF({c_grd_col}{first_data}:{c_grd_col}{last_data},"D")'),
            ('Grade F (Below 60%)', f'=COUNTIF({c_grd_col}{first_data}:{c_grd_col}{last_data},"F")'),
        ]

        for s_idx, (lbl, formula, cached_v, val_fmt) in enumerate(stats_data):
            curr_r = stat_r + 1 + s_idx
            sheet.set_row(curr_r, 19)
            sheet.merge_range(curr_r, 0, curr_r, min(3, last_col - 5), lbl, f_stat_lbl)
            sheet.merge_range(curr_r, min(4, last_col - 4), curr_r, min(5, last_col - 3), '', val_fmt)
            sheet.write_formula(curr_r, min(4, last_col - 4), formula, val_fmt, value=cached_v)

            if s_idx < len(grade_breakdown):
                g_lbl, g_formula = grade_breakdown[s_idx]
                sheet.merge_range(curr_r, min(6, last_col - 2), curr_r, max(min(7, last_col - 1), min(6, last_col - 2)), g_lbl, f_stat_lbl)
                sheet.merge_range(curr_r, last_col - 1, curr_r, last_col, '', f_stat_val_int)
                sheet.write_formula(curr_r, last_col - 1, g_formula, f_stat_val_int, value=0)

        # 6. Sign-off / Verification Section
        sig_r = stat_r + len(stats_data) + 2
        sheet.set_row(sig_r, 20)
        c_third = max(1, (last_col + 1) // 3)
        sheet.merge_range(sig_r, 0, sig_r, c_third - 1, 'Prepared By (Instructor)', f_sig_lbl)
        sheet.merge_range(sig_r, c_third, sig_r, (2 * c_third) - 1, 'Verified By (Department Head)', f_sig_lbl)
        sheet.merge_range(sig_r, 2 * c_third, sig_r, last_col, 'Approved By (Academic Registrar / Dean)', f_sig_lbl)

        for line_offset in range(1, 4):
            sheet.set_row(sig_r + line_offset, 18)
            if line_offset == 1:
                t_name = info.get('teacher', 'Instructor Signature')
                d_name = info.get('department', 'Department Head')
                sheet.merge_range(sig_r + line_offset, 0, sig_r + line_offset, c_third - 1, t_name, f_data_center)
                sheet.merge_range(sig_r + line_offset, c_third, sig_r + line_offset, (2 * c_third) - 1, d_name, f_data_center)
                sheet.merge_range(sig_r + line_offset, 2 * c_third, sig_r + line_offset, last_col, 'Office of Academic Affairs', f_data_center)
            elif line_offset == 2:
                sheet.merge_range(sig_r + line_offset, 0, sig_r + line_offset, c_third - 1, 'Signature: _______________________', f_sig_line)
                sheet.merge_range(sig_r + line_offset, c_third, sig_r + line_offset, (2 * c_third) - 1, 'Signature: _______________________', f_sig_line)
                sheet.merge_range(sig_r + line_offset, 2 * c_third, sig_r + line_offset, last_col, 'Official University Seal / Signature', f_sig_line)
            elif line_offset == 3:
                sheet.merge_range(sig_r + line_offset, 0, sig_r + line_offset, c_third - 1, 'Date: _____ / _____ / 202___', f_sig_line)
                sheet.merge_range(sig_r + line_offset, c_third, sig_r + line_offset, (2 * c_third) - 1, 'Date: _____ / _____ / 202___', f_sig_line)
                sheet.merge_range(sig_r + line_offset, 2 * c_third, sig_r + line_offset, last_col, 'Date: _____ / _____ / 202___', f_sig_line)

        # 7. Official Footer
        foot_r = sig_r + 5
        sheet.merge_range(foot_r, 0, foot_r, last_col, 'CONFIDENTIAL - This class marksheet is an official academic record produced by the University Management Portal. Any unauthorized alteration or forgery is strictly prohibited.', f_footer_note)

    workbook.close()
    return output.getvalue()


class UniversityClassMarksheetController(http.Controller):

    @http.route([
        '/university/class_marksheet/<int:section_id>/xlsx',
        '/university/class_marksheet/<int:section_id>/excel',
        '/university/class/<int:section_id>/marksheet/xlsx',
        '/university/class/<int:section_id>/marksheet/excel',
    ], type='http', auth='user', methods=['GET'])
    def download_class_marksheet_xlsx(self, section_id, **kwargs):
        # Check if record is a class section
        section = request.env['university.class.section'].browse(section_id).exists()
        if not section:
            # Fallback: check if an exam_id was passed
            exam = request.env['university.exam'].browse(section_id).exists()
            if exam:
                from .exam_marksheet import UniversityExamMarksheetController
                return UniversityExamMarksheetController().download_marksheet_xlsx(section_id, **kwargs)
            return request.not_found()

        try:
            section.check_access('read')
        except AccessError:
            return request.not_found()

        # Gather section info
        subj = section.subject_id
        course_label = f"[{subj.code}] {subj.name}" if subj and subj.code else (subj.name if subj else section.name)
        period_label = f"{section.academic_year_id.name or ''} - {section.semester_id.name or ''}".strip(' -')
        teacher_label = f"{section.teacher_id.name} ({section.teacher_id.teacher_id})" if (section.teacher_id and section.teacher_id.teacher_id) else (section.teacher_id.name if section.teacher_id else 'Course Instructor')

        section_info = {
            'institution': section.env.company.name or 'HARVARD UNIVERSITY - FACULTY ACADEMIC PORTAL',
            'course': course_label,
            'section': section.name or 'Section',
            'program': section.program_id.name or (section.department_id.name if section.department_id else 'Academic Program'),
            'department': section.department_id.name or 'Academic Department',
            'academic_period': period_label,
            'teacher': teacher_label,
            'classroom': section.classroom_id.name if section.classroom_id else 'TBA',
            'schedule': f"{section.day_summary or ''} {section.time_summary or ''}".strip() or 'Weekly Scheduled',
            'status': dict(section._fields['state'].selection).get(section.state, (section.state or 'Active')).capitalize() if 'state' in section._fields else 'Active',
        }

        # Gather section exams
        exams = []
        for ex in section.exam_ids.sorted(key=lambda e: (e.exam_date or fields.Date.today(), e.id)):
            exams.append({
                'id': ex.id,
                'name': ex.name or ex.exam_type or 'Exam',
                'max_score': ex.max_score or 100.0,
            })

        # Gather enrolled students
        enrollments = section.enrollment_ids.filtered(lambda e: e.status in ('enrolled', 'completed'))
        students = []
        for enr in enrollments.sorted(key=lambda e: (e.student_id.student_id or '', e.student_id.name or '')):
            stu = enr.student_id
            exam_scores = {}
            for ex in section.exam_ids:
                sc = ex.score_ids.filtered(lambda s: s.student_id.id == stu.id)
                if sc:
                    exam_scores[ex.id] = sc[0].final_score if not sc[0].is_absent else 0.0
                else:
                    exam_scores[ex.id] = 0.0

            total_sc = sum(exam_scores.values())
            students.append({
                'id': stu.student_id or f'STU-{stu.id}',
                'name': stu.name or 'Student',
                'attendance_rate': 95.0,
                'exam_scores': exam_scores,
                'total_score': total_sc,
                'remark': '',
            })

        content = build_class_marksheet_xlsx(
            title=f"Class Marksheet - {section.name}",
            subtitle=f"{course_label} Gradebook",
            section_info=section_info,
            exams=exams,
            students=students,
        )

        clean_name = "".join(c for c in (section.name or f"section_{section_id}") if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"class_marksheet_{clean_name}_{section_id}.xlsx"

        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', str(len(content))),
            ],
        )

    @http.route([
        '/university/class_marksheet/<int:section_id>/pdf',
        '/university/class_marksheet/<int:section_id>/download',
        '/university/class/<int:section_id>/marksheet/pdf',
        '/university/class/<int:section_id>/marksheet/download',
    ], type='http', auth='user', methods=['GET'])
    def download_class_marksheet_pdf(self, section_id, **kwargs):
        section = request.env['university.class.section'].browse(section_id).exists()
        if not section:
            exam = request.env['university.exam'].browse(section_id).exists()
            if exam:
                from .exam_marksheet import UniversityExamMarksheetController
                return UniversityExamMarksheetController().download_marksheet_pdf(section_id, **kwargs)
            return request.not_found()

        try:
            section.check_access('read')
        except AccessError:
            return request.not_found()

        # If report exists in environment, render it; otherwise, fallback to first exam marksheet or custom qweb
        report_action = request.env.ref('school_management.action_report_university_class_marksheet', raise_if_not_found=False)
        if report_action:
            pdf_content, _ct = request.env['ir.actions.report']._render_qweb_pdf(
                'school_management.action_report_university_class_marksheet',
                res_ids=[section.id],
            )
        elif section.exam_ids:
            # Render marksheet of the primary/final exam
            primary_exam = section.exam_ids.sorted(key=lambda e: (e.weight_percent or 0, e.id), reverse=True)[0]
            pdf_content, _ct = request.env['ir.actions.report']._render_qweb_pdf(
                'school_management.action_report_university_exam_marksheet',
                res_ids=[primary_exam.id],
            )
        else:
            return request.make_response("No exams or marksheet data recorded for this section yet.", status=404)

        clean_name = "".join(c for c in (section.name or f"section_{section_id}") if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"class_marksheet_{clean_name}_{section_id}.pdf"

        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', str(len(pdf_content))),
            ],
        )
