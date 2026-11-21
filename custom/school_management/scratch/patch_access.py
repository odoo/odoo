with open("security/ir.model.access.csv", "r", encoding="utf-8") as f:
    c = f.read()

target = "access_university_service_hour_student,university.service.hour.student,model_university_service_hour,school_management.group_school_student,1,1,1,0"
replacement = "access_university_service_hour_student,university.service.hour.student,model_university_service_hour,school_management.group_school_student,1,1,1,0\naccess_university_service_hour_teacher,university.service.hour.teacher,model_university_service_hour,school_management.group_university_teacher,1,1,1,0"

if target in c and "access_university_service_hour_teacher" not in c:
    c = c.replace(target, replacement, 1)
    with open("security/ir.model.access.csv", "w", encoding="utf-8") as f:
        f.write(c)
    print("Added service hour access for teacher in ir.model.access.csv")
else:
    print("Already present or target not found")
