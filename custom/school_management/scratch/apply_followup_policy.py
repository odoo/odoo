import re

# ==============================================================
# 1. Update custom/school_management/security/ir.model.access.csv
# ==============================================================
csv_path = 'custom/school_management/security/ir.model.access.csv'
with open(csv_path, 'r', encoding='utf-8') as f:
    csv_text = f.read()

# Replace HOD followup entry (change perm_unlink to 1)
old_hod_entry = 'access_university_student_followup_hod,university.student.followup.hod,model_university_student_followup,school_management.group_school_hod,1,1,1,0'
new_hod_entry = 'access_university_student_followup_hod,university.student.followup.hod,model_university_student_followup,school_management.group_school_hod,1,1,1,1'
assert old_hod_entry in csv_text, "old_hod_entry not found"
csv_text = csv_text.replace(old_hod_entry, new_hod_entry, 1)

# Ensure teacher entries have group_university_teacher and group_school_teacher
old_teacher_entry = 'access_university_student_followup_teacher,university.student.followup.student,model_university_student_followup,school_management.group_school_teacher,1,1,1,0'
new_teacher_entries = '''access_university_student_followup_teacher,university.student.followup.teacher,model_university_student_followup,school_management.group_university_teacher,1,1,1,0
access_university_student_followup_school_teacher,university.student.followup.school_teacher,model_university_student_followup,school_management.group_school_teacher,1,1,1,0
access_university_student_followup_dean,university.student.followup.dean,model_university_student_followup,school_management.group_school_dean,1,0,0,0
access_university_student_followup_registrar,university.student.followup.registrar,model_university_student_followup,school_management.group_school_registrar,1,0,0,0'''

assert old_teacher_entry in csv_text, "old_teacher_entry not found"
csv_text = csv_text.replace(old_teacher_entry, new_teacher_entries, 1)

with open(csv_path, 'w', encoding='utf-8', newline='') as f:
    f.write(csv_text)
print("Updated ir.model.access.csv")

# ==============================================================
# 2. Update custom/school_management/security/record_rules.xml
# ==============================================================
rr_path = 'custom/school_management/security/record_rules.xml'
with open(rr_path, 'r', encoding='utf-8') as f:
    rr_text = f.read()

old_followup_rules = '''    <!-- ==================== FOLLOW-UP ACTION RULES ==================== -->
    <record id="rule_followup_admin" model="ir.rule">
        <field name="name">Admin: all follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_admin'))]"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>

    <record id="rule_followup_hod" model="ir.rule">
        <field name="name">HOD: department student follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_hod'))]"/>
        <field name="domain_force">['|', ('department_id.head_id.user_id', '=', user.id), ('department_id.head_id', '=', user.teacher_id.id)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="False"/>
    </record>

    <record id="rule_followup_teacher" model="ir.rule">
        <field name="name">Teacher: own or advisee follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_university_teacher'))]"/>
        <field name="domain_force">['|', ('advisor_id.user_id', '=', user.id), '|', ('student_id.advisor_id.user_id', '=', user.id), ('student_id.enrollment_ids.section_id.teacher_id.user_id', '=', user.id)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="False"/>
    </record>

    <record id="rule_followup_student" model="ir.rule">
        <field name="name">Student: own visible follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_student'))]"/>
        <field name="domain_force">['&amp;', ('student_id.user_id', '=', user.id), ('visible_to_student', '=', True)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="False"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_unlink" eval="False"/>
    </record>'''

new_followup_rules = '''    <!-- ==================== FOLLOW-UP ACTION RULES ==================== -->
    <record id="rule_followup_admin" model="ir.rule">
        <field name="name">Admin: all follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_admin'))]"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>

    <record id="rule_followup_hod" model="ir.rule">
        <field name="name">HOD: department student follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_hod'))]"/>
        <field name="domain_force">['|', ('department_id.head_id.user_id', '=', user.id), ('department_id.head_id', '=', user.teacher_id.id)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>

    <record id="rule_followup_teacher" model="ir.rule">
        <field name="name">Teacher: advisee follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_university_teacher')), (4, ref('group_school_teacher'))]"/>
        <field name="domain_force">['|', ('advisor_id.user_id', '=', user.id), ('student_id.advisor_id.user_id', '=', user.id)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="False"/>
    </record>

    <record id="rule_followup_dean" model="ir.rule">
        <field name="name">Dean: faculty student follow-ups (read-only)</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_dean'))]"/>
        <field name="domain_force">['|', ('department_id.faculty_id.dean_id.user_id', '=', user.id), ('student_id.faculty_id.dean_id.user_id', '=', user.id)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="False"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_unlink" eval="False"/>
    </record>

    <record id="rule_followup_registrar" model="ir.rule">
        <field name="name">Registrar: all student follow-ups (read-only)</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_registrar'))]"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="False"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_unlink" eval="False"/>
    </record>

    <record id="rule_followup_student" model="ir.rule">
        <field name="name">Student: own visible follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_school_student'))]"/>
        <field name="domain_force">['&amp;', ('student_id.user_id', '=', user.id), ('visible_to_student', '=', True)]</field>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="False"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_unlink" eval="False"/>
    </record>'''

assert old_followup_rules in rr_text, "old_followup_rules not found"
rr_text = rr_text.replace(old_followup_rules, new_followup_rules, 1)

with open(rr_path, 'w', encoding='utf-8', newline='') as f:
    f.write(rr_text)
print("Updated record_rules.xml")

# ==============================================================
# 3. Update custom/school_management/models/advising.py
# ==============================================================
adv_path = 'custom/school_management/models/advising.py'
with open(adv_path, 'r', encoding='utf-8') as f:
    adv_text = f.read()

old_adv_end = '''    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset(self):
        self.write({"state": "pending"})'''

new_adv_end = '''    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset(self):
        self.write({"state": "pending"})

    def unlink(self):
        user = self.env.user
        is_admin = user.has_group("school_management.group_school_admin") or self.env.su
        is_hod = user.has_group("school_management.group_school_hod")
        for rec in self:
            if not is_admin and not is_hod:
                raise AccessError(_("You are not allowed to delete follow-up actions. Only Administrators and Department Heads can delete follow-up actions."))
            if is_hod and not is_admin:
                hod_user_id = rec.department_id.head_id.user_id.id if rec.department_id.head_id else False
                hod_teacher_id = rec.department_id.head_id.id if rec.department_id.head_id else False
                if hod_user_id != user.id and (not user.teacher_id or hod_teacher_id != user.teacher_id.id):
                    raise AccessError(_("Department Heads can only delete follow-up actions for students in their own department."))
        return super().unlink()'''

assert old_adv_end in adv_text, "old_adv_end not found"
adv_text = adv_text.replace(old_adv_end, new_adv_end, 1)

with open(adv_path, 'w', encoding='utf-8', newline='') as f:
    f.write(adv_text)
print("Updated advising.py")

# ==============================================================
# 4. Update custom/school_management/views/menu_views.xml
# ==============================================================
menu_path = 'custom/school_management/views/menu_views.xml'
with open(menu_path, 'r', encoding='utf-8') as f:
    menu_text = f.read()

old_menu_section = '''    <!-- Submenu: Student Advising -->
    <menuitem
        id="menu_university_advising_category"
        name="Student Advising"
        parent="menu_university_people"
        sequence="30"
        groups="school_management.group_school_admin,base.group_system"
    />
    <menuitem
        id="menu_university_advising_notes"
        name="Advising Notes"
        parent="menu_university_advising_category"
        action="action_university_student_advising_note"
        sequence="10"
        groups="school_management.group_school_admin,base.group_system"
    />
    <menuitem
        id="menu_university_student_followups"
        name="Follow-up Actions"
        parent="menu_university_advising_category"
        action="action_university_student_followup"
        sequence="20"
        groups="school_management.group_university_teacher,school_management.group_school_admin,base.group_system"
    />'''

new_menu_section = '''    <!-- Submenu: Student Advising -->
    <menuitem
        id="menu_university_advising_category"
        name="Student Advising"
        parent="menu_university_people"
        sequence="30"
        groups="school_management.group_university_teacher,school_management.group_school_teacher,school_management.group_school_hod,school_management.group_school_dean,school_management.group_school_registrar,school_management.group_school_admin,base.group_system"
    />
    <menuitem
        id="menu_university_advising_notes"
        name="Advising Notes"
        parent="menu_university_advising_category"
        action="action_university_student_advising_note"
        sequence="10"
        groups="school_management.group_school_admin,base.group_system"
    />
    <menuitem
        id="menu_university_student_followups"
        name="Follow-up Actions"
        parent="menu_university_advising_category"
        action="action_university_student_followup"
        sequence="20"
        groups="school_management.group_university_teacher,school_management.group_school_teacher,school_management.group_school_hod,school_management.group_school_dean,school_management.group_school_registrar,school_management.group_school_admin,base.group_system"
    />'''

assert old_menu_section in menu_text, "old_menu_section not found"
menu_text = menu_text.replace(old_menu_section, new_menu_section, 1)

with open(menu_path, 'w', encoding='utf-8', newline='') as f:
    f.write(menu_text)
print("Updated menu_views.xml")

print("All policy updates applied successfully!")
