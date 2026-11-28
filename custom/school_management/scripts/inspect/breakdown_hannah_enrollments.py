import sys
sys.path.insert(0, 'C:/Odoo/odoo')
import odoo
from odoo.modules.registry import Registry
from odoo import api

odoo.tools.config.parse_config(['-c', 'C:/Odoo/odoo/odoo.conf', '-d', 'odoo'])
reg = Registry('odoo')
with reg.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    student = env['university.student'].browse(6)
    print("Student:", student.name, student.program_id.name)
    enrollments = env['university.enrollment'].search([('student_id', '=', 6)])
    print(f"Total enrollments: {len(enrollments)}")
    by_year_sem = {}
    for e in enrollments:
        sec = e.section_id
        key = f"{sec.academic_year_id.name} - {sec.semester_id.name} ({sec.program_id.name})"
        by_year_sem.setdefault(key, []).append((sec.name, sec.subject_id.name, e.status))
    for k, v in by_year_sem.items():
        print(f"\n{k} ({len(v)} sections):")
        for sname, subname, status in v:
            print(f"   {sname}: {subname} [{status}]")
