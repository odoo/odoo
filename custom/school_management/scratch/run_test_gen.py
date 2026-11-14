import sys
sys.path.insert(0, 'C:/Odoo/odoo')
sys.path.insert(0, 'C:/Odoo/odoo/custom/school_management/scratch')
import odoo
from odoo.tools import config
config.parse_config(['-c', 'C:/Odoo/odoo/odoo.conf'])
from odoo.modules.registry import Registry
from odoo import api
from test_full_marksheet import build_marksheet_xlsx

reg = Registry('odoo')
with reg.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    exam = env['university.exam'].browse(910)
    
    exam_type_label = dict(exam._fields['exam_type'].selection).get(exam.exam_type, (exam.exam_type or 'Exam').capitalize())
    state_label = dict(exam._fields['state'].selection).get(exam.state, (exam.state or '').capitalize())
    course_label = f"[{exam.subject_id.code}] {exam.subject_id.name}" if exam.subject_id.code else (exam.subject_id.name or 'Subject')
    period_label = f"{exam.academic_year_id.name or ''} - {exam.semester_id.name or ''}".strip(' -')
    teacher_label = f"{exam.teacher_id.name} ({exam.teacher_id.teacher_id})" if exam.teacher_id.teacher_id else (exam.teacher_id.name or 'Teacher')
    duration_str = f"{exam.duration_minutes} minutes" if exam.duration_minutes else 'Standard Duration'
    date_str = str(exam.exam_date) if exam.exam_date else 'TBA'
    date_duration_label = f"{date_str} ({duration_str})"
    
    exam_info = {
        'institution': exam.env.company.name or 'HARVARD UNIVERSITY',
        'course': course_label,
        'section': exam.section_id.name or 'N/A',
        'program': exam.program_id.name or 'N/A',
        'academic_period': period_label,
        'teacher': teacher_label,
        'department': exam.department_id.name or 'Academic Department',
        'weight': f"{exam.weight_percent:.1f}%" if exam.weight_percent else 'N/A',
        'exam_type': exam_type_label,
        'exam_date_duration': date_duration_label,
        'status': state_label,
        'avg_score': exam.average_score or 0.0,
    }
    
    students = []
    for score in exam.score_ids.sorted(key=lambda s: (s.student_code or '', s.student_id.name or '')):
        students.append({
            'id': score.student_code or score.student_id.student_id or f'STU-{score.student_id.id}',
            'name': score.student_id.name or '',
            'is_absent': score.is_absent,
            'raw_score': score.score,
            'penalty': score.penalty_applied or 0.0,
            'final_score': score.final_score if not score.is_absent else 0.0,
            'percentage': score.percentage or 0.0,
            'remark': score.remark or '',
        })
        
    full_marks = exam.max_score or 100.0
    pass_marks = round(full_marks * 0.5, 2)
    
    content = build_marksheet_xlsx(
        title=exam.name,
        subtitle=f"{exam_type_label} Marksheet",
        full_marks=full_marks,
        pass_marks=pass_marks,
        subjects=[exam.subject_id.name],
        students=students,
        exam_info=exam_info
    )
    with open('C:/Odoo/odoo/custom/school_management/scratch/test_marksheet_910.xlsx', 'wb') as f:
        f.write(content)
    print('Successfully generated marksheet! File size:', len(content))
