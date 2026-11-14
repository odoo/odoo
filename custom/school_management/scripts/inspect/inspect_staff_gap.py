import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry

def inspect_gaps():
    odoo.tools.config.parse_config(['-c', 'odoo.conf', '-d', 'odoo'])
    registry = Registry('odoo')
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        Teacher = env['university.teacher']
        Section = env['university.class.section']
        Slot = env['university.timetable.slot']
        Attendance = env['university.staff.attendance']
        Faculty = env['university.faculty']
        Department = env['university.department']
        Assignment = env['university.academic.assignment']

        print("=== TEACHERS WITHOUT TIMETABLE SESSIONS ===")
        no_slot_teachers = Teacher.search([]).filtered(lambda t: len(t.timetable_slot_ids) == 0)
        print(f"Teachers without any slots: {len(no_slot_teachers)} / {len(Teacher.search([]))}")
        for t in no_slot_teachers:
            print(f"  - {t.display_name} ({t.teacher_id}) | Dept: {t.department_id.name} | Sections: {len(t.section_ids)}")

        print("\n=== CLASS SECTIONS WITHOUT TIMETABLE SLOTS ===")
        sections = Section.search([])
        no_slot_sections = [s for s in sections if Slot.search_count([('section_id', '=', s.id)]) == 0]
        print(f"Sections without slots: {len(no_slot_sections)} / {len(sections)}")
        for s in no_slot_sections[:15]:
            t_name = s.teacher_id.name if s.teacher_id else "No Teacher"
            print(f"  - Section {s.name} ({s.subject_id.code if s.subject_id else 'No Sub'}) -> Teacher: {t_name}")

        print("\n=== FACULTIES WITHOUT DEANS ===")
        for f in Faculty.search([('active', '=', True)]):
            deans = Assignment.search([('faculty_id', '=', f.id), ('role', '=', 'dean'), ('active', '=', True)])
            if not deans:
                print(f"  - Faculty missing Dean: {f.name}")

        print("\n=== DEPARTMENTS WITHOUT HODs ===")
        for d in Department.search([('active', '=', True)]):
            hods = Assignment.search([('department_id', '=', d.id), ('role', '=', 'department_head'), ('active', '=', True)])
            if not hods:
                print(f"  - Department missing HOD: {d.name} (Faculty: {d.faculty_id.name})")

        print("\n=== TEACHERS WITHOUT ATTENDANCE LOGS ===")
        no_att_teachers = Teacher.search([]).filtered(lambda t: len(t.attendance_ids) == 0)
        print(f"Teachers without attendance records: {len(no_att_teachers)} / {len(Teacher.search([]))}")

if __name__ == '__main__':
    inspect_gaps()
