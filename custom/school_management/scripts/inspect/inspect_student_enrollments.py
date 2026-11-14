import sys
sys.path.insert(0, 'C:/Odoo/odoo')
import odoo
from odoo.modules.registry import Registry
from odoo import api

odoo.tools.config.parse_config(['-c', 'C:/Odoo/odoo/odoo.conf', '-d', 'odoo'])
reg = Registry('odoo')
with reg.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    student_user = env['res.users'].search([('login', '=', 'student')], limit=1)
    print("Student user:", student_user.id, student_user.name)
    student = env['university.student'].search([('user_id', '=', student_user.id)], limit=1)
    print("Student record:", student.id, student.name, student.program_id.name)
    
    enrollments = env['university.enrollment'].search([('student_id', '=', student.id)])
    print(f"Total enrollments for Hannah: {len(enrollments)}")
    for e in enrollments[:10]:
        print(f" - Section: {e.section_id.name} | Status: {e.status} | Semester: {e.section_id.semester_id.name} | AY: {e.section_id.academic_year_id.name} | Program: {e.section_id.program_id.name}")
    
    # What does action 836 do?
    act = env['ir.actions.act_window'].search([('res_model', '=', 'university.class.section'), ('name', '=', 'My Classes')], limit=1)
    if act:
        print("Action My Classes:", act.id, act.domain, act.context)
        student_env = env['university.class.section'].with_user(student_user)
        visible_sections = student_env.search([])
        print(f"Sections visible to student user via search([]): {len(visible_sections)}")
        current_semester = env['university.semester'].search([('is_current', '=', True)], limit=1)
        print("Current semester:", current_semester.name if current_semester else "None")
