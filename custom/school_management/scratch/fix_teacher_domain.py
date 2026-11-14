with open('custom/school_management/security/record_rules.xml', 'r', encoding='utf-8') as f:
    text = f.read()

old_domain = """    <record id="rule_followup_teacher" model="ir.rule">
        <field name="name">Teacher: advisee follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_university_teacher')), (4, ref('group_school_teacher'))]"/>
        <field name="domain_force">['|', ('advisor_id.user_id', '=', user.id), ('student_id.advisor_id.user_id', '=', user.id)]</field>"""

new_domain = """    <record id="rule_followup_teacher" model="ir.rule">
        <field name="name">Teacher: advisee follow-ups</field>
        <field name="model_id" ref="model_university_student_followup"/>
        <field name="groups" eval="[(4, ref('group_university_teacher')), (4, ref('group_school_teacher'))]"/>
        <field name="domain_force">[('student_id.advisor_id.user_id', '=', user.id)]</field>"""

assert old_domain in text, "old_domain not found"
text = text.replace(old_domain, new_domain, 1)

with open('custom/school_management/security/record_rules.xml', 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Updated rule_followup_teacher domain")
