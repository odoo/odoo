import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry

def audit():
    odoo.tools.config.parse_config(['-c', 'odoo.conf', '-d', 'odoo'])
    registry = Registry('odoo')
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        Teacher = env['university.teacher']
        Assignment = env['university.academic.assignment']
        Attendance = env['university.staff.attendance']
        Slot = env['university.timetable.slot']
        Section = env['university.class.section']
        Faculty = env['university.faculty']
        Department = env['university.department']
        
        print('=== ACADEMIC STAFF ECOSYSTEM AUDIT ===')
        print(f'Total Teachers: {Teacher.search_count([])}')
        print(f'Total Faculties: {Faculty.search_count([])}')
        print(f'Total Departments: {Department.search_count([])}')
        print(f'Total Role Assignments: {Assignment.search_count([])}')
        print(f'Active Deans: {Assignment.search_count([("role", "=", "dean"), ("active", "=", True)])}')
        print(f'Active HODs: {Assignment.search_count([("role", "=", "department_head"), ("active", "=", True)])}')
        print(f'Total Staff Attendance Records: {Attendance.search_count([])}')
        print(f'Total Timetable Slots: {Slot.search_count([])}')
        print(f'Slots with Teacher Assigned: {Slot.search_count([("teacher_id", "!=", False)])}')
        print(f'Slots without Teacher: {Slot.search_count([("teacher_id", "=", False)])}')
        
        d_aaker = Teacher.search([('name', 'ilike', 'Aaker')], limit=1)
        if d_aaker:
            print(f'\n--- Teacher: {d_aaker.name} ({d_aaker.teacher_id}) ---')
            print(f'  Position: {d_aaker.position}')
            print(f'  Department: {d_aaker.department_id.name}')
            print(f'  Faculty: {d_aaker.faculty_id.name}')
            print(f'  Sections: {len(d_aaker.section_ids)}')
            print(f'  Timetable Sessions: {len(d_aaker.timetable_slot_ids)}')
            print(f'  Attendance Logs: {len(d_aaker.attendance_ids)}')
            print(f'  Role Assignments: {len(d_aaker.assignment_ids)}')
            print(f'  Is Head: {d_aaker.is_head}, Is Dean: {d_aaker.is_dean}, Is HOD: {d_aaker.is_hod}')
            print(f'  Notes: {d_aaker.notes}')

        print('\n--- ALL ROLE ASSIGNMENTS ---')
        for asg in Assignment.search([]):
            print(f'  [{asg.role}] {asg.staff_id.name} -> Faculty: {asg.faculty_id.name if asg.faculty_id else "None"} | Dept: {asg.department_id.name if asg.department_id else "None"} (Active: {asg.active}, Start: {asg.start_date})')

        print('\n--- TEACHERS ATTENDANCE SUMMARY ---')
        teachers_with_att = Teacher.search([]).filtered(lambda t: len(t.attendance_ids) > 0)
        print(f'Teachers with Attendance Records: {len(teachers_with_att)} / {len(Teacher.search([]))}')

        print('\n--- TEACHERS TIMETABLE SESSIONS SUMMARY ---')
        teachers_with_slots = Teacher.search([]).filtered(lambda t: len(t.timetable_slot_ids) > 0)
        print(f'Teachers with Timetable Sessions: {len(teachers_with_slots)} / {len(Teacher.search([]))}')

if __name__ == '__main__':
    audit()
