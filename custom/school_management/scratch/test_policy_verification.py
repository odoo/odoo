import os
import sys

# Setup Odoo environment
sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo import api, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.modules.registry import Registry

odoo.tools.config.parse_config(["-c", r"C:\Odoo\odoo\odoo.conf", "-d", "odoo"])

registry = Registry("odoo")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Followup = env["university.student.followup"]
    Student = env["university.student"]
    Teacher = env["university.teacher"]
    Department = env["university.department"]
    Faculty = env["university.faculty"]
    
    # 1. Identify or setup test groups
    group_admin = env.ref("school_management.group_school_admin")
    group_hod = env.ref("school_management.group_school_hod")
    group_teacher = env.ref("school_management.group_school_teacher")
    group_dean = env.ref("school_management.group_school_dean")
    group_registrar = env.ref("school_management.group_school_registrar")
    group_student = env.ref("school_management.group_school_student")
    
    # Setup test departments and faculties
    dept_cs = Department.search([("name", "ilike", "Computer Science")], limit=1)
    if not dept_cs:
        dept_cs = Department.search([], limit=1)
    dept_other = Department.search([("id", "!=", dept_cs.id)], limit=1)
    
    print(f"Testing with Dept CS: {dept_cs.name}, Other Dept: {dept_other.name}")

    # ==============================================================
    # Test 1: TEACHER
    # Scope: Students they advise
    # Permissions: Create and move follow-ups, no delete
    # ==============================================================
    # Pick pure teacher user
    teacher_user = env["res.users"].search([("login", "=", "teacher")], limit=1)
    if not teacher_user:
        teacher_user = env["res.users"].search([("group_ids", "in", [group_teacher.id]), ("group_ids", "not in", [group_hod.id, group_dean.id, group_admin.id])], limit=1)
    teacher_rec = teacher_user.teacher_id
    if not teacher_rec:
        teacher_rec = Teacher.create({
            "name": "Teacher Test",
            "teacher_id": "TEST-T-01",
            "user_id": teacher_user.id,
            "department_id": dept_cs.id,
        })
    
    student_user = env["res.users"].search([("login", "=", "student")], limit=1)
    advisee_student = Student.search([("user_id", "=", student_user.id)], limit=1)
    if not advisee_student:
        advisee_student = Student.search([("department_id", "=", dept_cs.id)], limit=1)
        advisee_student.user_id = student_user.id
    advisee_student.advisor_id = teacher_rec.id
        
    other_student = Student.search([("advisor_id", "!=", teacher_rec.id), ("id", "!=", advisee_student.id)], limit=1)
    
    print(f"Teacher User: {teacher_user.login} ({teacher_rec.name})")
    print(f"Advisee Student: {advisee_student.name} (id={advisee_student.id})")
    print(f"Other Student (not advisee): {other_student.name} (id={other_student.id})")
    
    # Environment as Teacher
    env_teacher = api.Environment(cr, teacher_user.id, {})
    
    # Teacher CAN create follow-up for advisee
    f_advisee = env_teacher["university.student.followup"].create({
        "title": "Policy Test Advisee Followup",
        "student_id": advisee_student.id,
        "action_type": "meeting",
        "visible_to_student": True,
    })
    print("[PASS] Teacher created follow-up for advisee successfully.")
    
    # Teacher CAN move follow-up (state change)
    f_advisee.action_start()
    assert f_advisee.state == "in_progress", "Teacher should be able to start progress"
    f_advisee.action_complete()
    assert f_advisee.state == "completed", "Teacher should be able to complete follow-up"
    print("[PASS] Teacher moved follow-up states (pending -> in_progress -> completed) successfully.")
    
    # Teacher CANNOT delete follow-up
    try:
        f_advisee.unlink()
        assert False, "Teacher should NOT be able to delete follow-up"
    except AccessError as e:
        print(f"[PASS] Teacher delete blocked with AccessError: {e}")

    # Teacher CANNOT create follow-up for non-advisee
    try:
        env_teacher["university.student.followup"].create({
            "title": "Policy Test Non-advisee Followup",
            "student_id": other_student.id,
            "action_type": "meeting",
        })
        assert False, "Teacher should NOT be able to create follow-up for non-advisee"
    except AccessError as e:
        print(f"[PASS] Teacher create for non-advisee blocked with AccessError: {e}")

    # Teacher CANNOT see follow-ups of non-advisees
    f_other = Followup.sudo().create({
        "title": "Policy Test Other Student Followup",
        "student_id": other_student.id,
        "advisor_id": teacher_rec.id,
        "action_type": "tutoring",
    })
    teacher_visible_ids = env_teacher["university.student.followup"].search([]).ids
    assert f_other.id not in teacher_visible_ids, "Teacher should not see non-advisee follow-up"
    print("[PASS] Teacher search correctly excludes non-advisee follow-ups.")
    
    # ==============================================================
    # Test 2: HOD
    # Scope: Students in department they manage
    # Permissions: Create, edit, delete, cancel
    # ==============================================================
    # Find or set HOD user for dept_cs
    hod_teacher = dept_cs.head_id
    if not hod_teacher or not hod_teacher.user_id:
        hod_user = env["res.users"].search([("login", "=", "hod")], limit=1)
        if not hod_user:
            hod_user = env["res.users"].create({
                "name": "HOD Test User",
                "login": "hod_test",
                "email": "hod_test@university.edu",
                "group_ids": [(6, 0, [env.ref("base.group_user").id, group_hod.id])],
            })
        if not hod_teacher:
            hod_teacher = env["university.teacher"].create({
                "name": "Dr. HOD Test",
                "teacher_id": "TEST-HOD-01",
                "user_id": hod_user.id,
                "department_id": dept_cs.id,
            })
        else:
            hod_teacher.user_id = hod_user.id
        dept_cs.head_id = hod_teacher.id
    else:
        hod_user = hod_teacher.user_id
        if group_hod not in hod_user.group_ids:
            hod_user.write({"group_ids": [(4, group_hod.id)]})

    env_hod = api.Environment(cr, hod_user.id, {})
    
    # HOD can create follow-up for student in their department
    dept_cs_student = Student.search([("department_id", "=", dept_cs.id)], limit=1)
    f_hod = env_hod["university.student.followup"].create({
        "title": "Policy Test HOD Followup",
        "student_id": dept_cs_student.id,
        "action_type": "warning",
    })
    print("[PASS] HOD created follow-up for department student.")
    
    # HOD can cancel follow-up
    f_hod.action_cancel()
    assert f_hod.state == "cancelled", "HOD should be able to cancel follow-up"
    print("[PASS] HOD cancelled follow-up.")
    
    # HOD can delete follow-up in own department
    f_hod.unlink()
    print("[PASS] HOD deleted follow-up in own department.")
    
    # ==============================================================
    # Test 3: REGISTRAR
    # Scope: All students
    # Permissions: Read only
    # ==============================================================
    registrar_user = env["res.users"].search([("group_ids", "in", [group_registrar.id])], limit=1)
    if not registrar_user:
        registrar_user = env["res.users"].create({
            "name": "Registrar Test User",
            "login": "reg_test",
            "email": "reg_test@university.edu",
            "group_ids": [(6, 0, [env.ref("base.group_user").id, group_registrar.id])],
        })
    env_reg = api.Environment(cr, registrar_user.id, {})
    
    # Registrar can read follow-ups
    reg_fups = env_reg["university.student.followup"].search([])
    assert f_advisee.id in reg_fups.ids and f_other.id in reg_fups.ids, "Registrar should see all student follow-ups"
    print(f"[PASS] Registrar can read all follow-ups (found {len(reg_fups)}).")
    
    # Registrar CANNOT create follow-up
    try:
        env_reg["university.student.followup"].create({
            "title": "Policy Test Registrar Followup",
            "student_id": advisee_student.id,
        })
        assert False, "Registrar should NOT be able to create follow-up"
    except AccessError as e:
        print(f"[PASS] Registrar create blocked with AccessError: {e}")
        
    # Registrar CANNOT delete follow-up
    try:
        f_advisee.with_user(registrar_user).unlink()
        assert False, "Registrar should NOT be able to delete follow-up"
    except AccessError as e:
        print(f"[PASS] Registrar delete blocked with AccessError: {e}")

    # ==============================================================
    # Test 4: DEAN
    # Scope: Their faculty
    # Permissions: Read only
    # ==============================================================
    # Identify dean
    dean_user = env["res.users"].search([("group_ids", "in", [group_dean.id]), ("teacher_id", "!=", False)], limit=1)
    if not dean_user:
        dean_user = env["res.users"].search([("group_ids", "in", [group_dean.id])], limit=1)
    
    faculty = dept_cs.faculty_id
    if faculty and not faculty.dean_id:
        if dean_user and dean_user.teacher_id:
            faculty.dean_id = dean_user.teacher_id.id
            
    if dean_user and faculty and faculty.dean_id and faculty.dean_id.user_id == dean_user:
        env_dean = api.Environment(cr, dean_user.id, {})
        dean_fups = env_dean["university.student.followup"].search([])
        print(f"[PASS] Dean can read faculty follow-ups (found {len(dean_fups)}).")
        
        # Dean CANNOT delete follow-up
        try:
            f_advisee.with_user(dean_user).unlink()
            assert False, "Dean should NOT be able to delete follow-up"
        except AccessError as e:
            print(f"[PASS] Dean delete blocked with AccessError: {e}")

    # ==============================================================
    # Test 5: STUDENT
    # Scope: Own records
    # Permissions: Read only (visible_to_student=True)
    # ==============================================================
    env_student = api.Environment(cr, student_user.id, {})
    
    # Student CAN read visible follow-up
    st_fups = env_student["university.student.followup"].search([])
    assert f_advisee.id in st_fups.ids, "Student should see own visible follow-up"
    print(f"[PASS] Student can read own visible follow-up only (found {len(st_fups)}).")
    
    # Hidden follow-up cannot be seen
    f_hidden = Followup.sudo().create({
        "title": "Secret Internal Note",
        "student_id": advisee_student.id,
        "advisor_id": teacher_rec.id,
        "visible_to_student": False,
    })
    st_fups_2 = env_student["university.student.followup"].search([])
    assert f_hidden.id not in st_fups_2.ids, "Student should NOT see hidden follow-up"
    print("[PASS] Student cannot see non-visible follow-up.")

    # Student CANNOT delete follow-up
    try:
        f_advisee.with_user(student_user).unlink()
        assert False, "Student should NOT be able to delete follow-up"
    except AccessError as e:
        print(f"[PASS] Student delete blocked with AccessError: {e}")

    # ==============================================================
    # Test 6: ADMIN
    # Scope: All students
    # Permissions: Everything including delete
    # ==============================================================
    Followup.browse(f_advisee.id).unlink()
    Followup.browse(f_other.id).unlink()
    Followup.browse(f_hidden.id).unlink()
    print("[PASS] Admin can delete all follow-ups.")
    
    cr.rollback()
    print("\nALL POLICY VERIFICATION TESTS PASSED SUCCESSFULLY!")
