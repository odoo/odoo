menu_path = "custom/school_management/views/menu_views.xml"
with open(menu_path, "r", encoding="utf-8") as f:
    xml = f.read()

target = """    <menuitem
        id="menu_university_timetable_sessions"
        name="Scheduled Sessions"
        parent="menu_university_sec_timetable"
        action="action_university_timetable_slot"
        sequence="10"
        groups="school_management.group_university_teacher,school_management.group_school_hod,school_management.group_school_admin,base.group_system"
    />"""

replacement = """    <menuitem
        id="menu_university_timetable_sessions"
        name="Schedule by Resource"
        parent="menu_university_sec_timetable"
        action="action_university_timetable_slot"
        sequence="10"
        groups="school_management.group_university_teacher,school_management.group_school_teacher,school_management.group_school_hod,school_management.group_school_dean,school_management.group_school_admin,school_management.group_school_timetable_manager,base.group_system"
    />"""

if target in xml:
    xml = xml.replace(target, replacement, 1)
    with open(menu_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print("Updated menu_views.xml to Schedule by Resource")
else:
    print("Warning: target menuitem not found in menu_views.xml")
