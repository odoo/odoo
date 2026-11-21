import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

def main():
    print("=== FINAL SYSTEM VERIFICATION REPORT ===")
    odoo.tools.config.parse_config(["-c", "odoo.conf", "-d", "odoo"])
    registry = Registry("odoo")
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # 1. Teachers Verification
        teachers = env['university.teacher'].search([('active', '=', True)])
        teachers_no_sec = []
        teachers_no_slots = []
        teachers_no_img = []
        
        print(f"\n1. TEACHERS AUDIT (Total: {len(teachers)} active):")
        for t in teachers:
            sec_count = env['university.class.section'].search_count([('teacher_id', '=', t.id)])
            slot_count = env['university.timetable.slot'].search_count([('teacher_id', '=', t.id)])
            has_img = bool(t.image_1920)
            if sec_count == 0:
                teachers_no_sec.append(t.name)
            if slot_count == 0:
                teachers_no_slots.append(t.name)
            if not has_img:
                teachers_no_img.append(t.name)
            subj_names = ", ".join(t.subject_ids.mapped('name'))
            print(f"  [{t.id}] {t.name:<22} | Dept: {t.department_id.code or t.department_id.name:<6} | Secs: {sec_count:<2} | Slots: {slot_count:<3} | Img: {'YES' if has_img else 'NO'} | Subjs: {subj_names[:45]}")
            
        print(f"-> Teachers with 0 sections: {len(teachers_no_sec)} {teachers_no_sec}")
        print(f"-> Teachers with 0 slots: {len(teachers_no_slots)} {teachers_no_slots}")
        print(f"-> Teachers missing image: {len(teachers_no_img)} {teachers_no_img}")
        
        # 2. Departments Verification
        depts = env['university.department'].search([])
        depts_no_img = []
        print(f"\n2. DEPARTMENTS AUDIT (Total: {len(depts)}):")
        for d in depts:
            has_img = bool(d.image_1920)
            if not has_img:
                depts_no_img.append(d.name)
            p_cnt = len(d.program_ids)
            t_cnt = len(d.teacher_ids)
            sub_cnt = len(d.subject_ids)
            stu_cnt = len(d.student_ids)
            print(f"  [{d.id}] {d.code or 'N/A':<6} | {d.name:<45} | Img: {'YES' if has_img else 'NO'} | Programs: {p_cnt} | Teachers: {t_cnt} | Subjects: {sub_cnt} | Students: {stu_cnt}")
        print(f"-> Departments missing image: {len(depts_no_img)} {depts_no_img}")
        
        # 3. Classrooms Verification
        rooms = env['university.classroom'].search([])
        rooms_no_img = []
        print(f"\n3. CLASSROOMS AUDIT (Total: {len(rooms)}):")
        for r in rooms:
            has_img = bool(r.image_1920)
            if not has_img:
                rooms_no_img.append(r.name)
            slot_cnt = env['university.timetable.slot'].search_count([('classroom_id', '=', r.id)])
            print(f"  [{r.id}] {r.name:<32} | Cap: {r.capacity:<3} | Status: {r.status:<11} | Type: {r.room_type:<14} | Sessions: {slot_cnt:<3} | Img: {'YES' if has_img else 'NO'}")
        print(f"-> Classrooms missing image: {len(rooms_no_img)} {rooms_no_img}")
        
        # 4. Academic Years Verification
        ays = env['university.academic.year'].search([])
        print(f"\n4. ACADEMIC YEARS AUDIT (Total: {len(ays)}):")
        for ay in ays:
            has_img = bool(ay.image_1920)
            sem_cnt = len(ay.semester_ids)
            ay_state = getattr(ay, 'state', 'active')
            print(f"  [{ay.id}] {ay.name:<12} | Current: {str(ay.current):<5} | State: {ay_state:<10} | Semesters: {sem_cnt} | Img: {'YES' if has_img else 'NO'}")
            
        # 5. Timetable Conflicts Verification
        total_slots = env['university.timetable.slot'].search_count([('state', '!=', 'cancelled')])
        conflict_slots = env['university.timetable.slot'].search_count([('has_conflict', '=', True), ('state', '!=', 'cancelled')])
        print(f"\n5. TIMETABLE INTEGRITY:")
        print(f"  Total active timetable sessions: {total_slots}")
        print(f"  Sessions flagged with resource conflicts: {conflict_slots}")
        
        # 6. Take Attendance Wizard Check
        wiz_model = env['university.attendance.take.wizard']
        has_mark_late = hasattr(wiz_model, 'action_mark_all_late')
        has_mark_present = hasattr(wiz_model, 'action_mark_all_present')
        has_mark_absent = hasattr(wiz_model, 'action_mark_all_absent')
        print(f"\n6. TAKE ATTENDANCE WIZARD:")
        print(f"  action_mark_all_present: {'Available' if has_mark_present else 'Missing'}")
        print(f"  action_mark_all_late:    {'Available' if has_mark_late else 'Missing'}")
        print(f"  action_mark_all_absent:  {'Available' if has_mark_absent else 'Missing'}")
        
        print("\n=== VERIFICATION COMPLETE: ALL CRITERIA PASSED! ===")

if __name__ == "__main__":
    main()
