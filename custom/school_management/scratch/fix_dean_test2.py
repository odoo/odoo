path = 'custom/school_management/scratch/test_policy_verification.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

old_block = """    dean_teacher = env["university.teacher"].search([("user_id", "=", dean_user.id)], limit=1)
    if not dean_teacher:
        dean_teacher = env["university.teacher"].create({
            "name": "Dean Teacher",
            "teacher_id": "TEST-DEAN-01",
            "user_id": dean_user.id,
            "faculty_id": faculty.id,
        })
    env["university.academic.assignment"].create({
        "staff_id": dean_teacher.id,
        "faculty_id": faculty.id,
        "role": "dean",
        "active": True,
        "start_date": "2026-01-01",
    })
    faculty._compute_dean_id()
    if not dept_cs.faculty_id:
        dept_cs.faculty_id = faculty.id
    advisee_student.faculty_id = faculty.id
    env_dean = api.Environment(cr, dean_user.id, {})"""

new_block = """    if faculty.dean_id:
        dean_teacher = faculty.dean_id
        dean_teacher.user_id = dean_user.id
    else:
        dean_teacher = env["university.teacher"].search([("user_id", "=", dean_user.id)], limit=1)
        if not dean_teacher:
            dean_teacher = env["university.teacher"].create({
                "name": "Dean Teacher",
                "teacher_id": "TEST-DEAN-01",
                "user_id": dean_user.id,
                "faculty_id": faculty.id,
            })
        env["university.academic.assignment"].create({
            "staff_id": dean_teacher.id,
            "faculty_id": faculty.id,
            "role": "dean",
            "active": True,
            "start_date": "2026-01-01",
        })
        faculty._compute_dean_id()
    if not dept_cs.faculty_id:
        dept_cs.faculty_id = faculty.id
    advisee_student.faculty_id = faculty.id
    env_dean = api.Environment(cr, dean_user.id, {})"""

assert old_block in text, "old_block not found"
text = text.replace(old_block, new_block, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Updated Dean assignment in test script")
